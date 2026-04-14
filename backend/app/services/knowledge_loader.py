"""知识库加载服务。

该服务负责将来自各种数据源的文档导入到 RAG 知识库中。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.data.vector import insert_document
from app.rag.embeddings import EmbeddingService
from app.wrappers.rootdata import ProjectInfo, scrape_rootdata_projects

logger = logging.getLogger(__name__)

# 本地存储爬取文档的基础目录
KB_DOCS_DIR = Path(__file__).parent.parent.parent / "data" / "kb_docs"


class KnowledgeLoader:
    """将文档加载到知识库的服务。"""

    def __init__(self, save_local: bool = True):
        """初始化知识库加载器。

        Args:
            save_local: 是否将爬取的文档保存到本地文件
        """
        self.embedding_service: Optional[EmbeddingService] = None
        self.save_local = save_local

        # 确保本地存储目录存在
        if self.save_local:
            for subdir in ["rootdata", "odaily", "tokenomics"]:
                (KB_DOCS_DIR / subdir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage ready: {KB_DOCS_DIR}")

    async def get_embedding_service(self) -> EmbeddingService:
        """获取或创建嵌入服务。"""
        if self.embedding_service is None:
            from app.rag.embeddings import get_embedding_service

            self.embedding_service = await get_embedding_service()
        return self.embedding_service

    async def import_rootdata_projects(
        self,
        limit: int = 20,
        embed: bool = True,
        import_to_kg: bool = False,
    ) -> dict:
        """将 Rootdata 项目导入知识库。

        Args:
            limit: 最大导入项目数
            embed: 是否立即生成嵌入
            import_to_kg: 是否同时导入 Neo4j 知识图谱

        Returns:
            包含导入统计信息的字典
        """
        logger.info(f"Starting Rootdata import (limit: {limit}, import_to_kg: {import_to_kg})")

        stats = {
            "fetched": 0,
            "imported": 0,
            "embedded": 0,
            "failed": 0,
            "errors": [],
            "kg_stats": None,
        }

        try:
            # 从 Rootdata 获取项目
            projects = await scrape_rootdata_projects(limit=limit)
            stats["fetched"] = len(projects)

            logger.info(f"Fetched {len(projects)} projects from Rootdata")

            # 先导入 Neo4j 知识图谱（如果请求的话）
            kg_client = None
            if import_to_kg:
                try:
                    from app.kg.client import Neo4jClient
                    from app.kg.importers import import_rootdata_to_kg

                    logger.info("Importing to Neo4j Knowledge Graph...")
                    kg_client = Neo4jClient()
                    await kg_client.connect()
                    kg_stats = await import_rootdata_to_kg(kg_client, projects, skip_existing=True)
                    stats["kg_stats"] = kg_stats
                    logger.info(f"KG import complete: {kg_stats['success']} projects")
                finally:
                    if kg_client:
                        await kg_client.close()

            # 将每个项目导入 RAG 知识库
            for project in projects:
                try:
                    # 转换为知识库文档格式
                    doc_data = project.to_kb_document()

                    # 保存到本地文件
                    self._save_to_local(
                        source="rootdata",
                        doc_id=project.rootdata_id,
                        title=doc_data["title"],
                        content=doc_data["content"],
                        url=doc_data.get("source_url"),
                        metadata=doc_data.get("metadata", {}),
                    )

                    # 插入数据库
                    doc_id = await insert_document(
                        title=doc_data["title"],
                        content=doc_data["content"],
                        source_url=doc_data.get("source_url"),
                        source_type=doc_data.get("source_type", "rootdata"),
                        metadata=doc_data.get("metadata", {}),
                    )

                    logger.info(f"Imported project: {project.name} (doc_id: {doc_id})")
                    stats["imported"] += 1

                except Exception as e:
                    logger.error(f"Failed to import project {project.name}: {e}")
                    stats["failed"] += 1
                    stats["errors"].append(f"{project.name}: {str(e)}")

            # 如果请求则生成嵌入
            if embed and stats["imported"] > 0:
                stats["embedded"] = await self._embed_recent_documents(stats["imported"])

        except Exception as e:
            logger.error(f"Error during Rootdata import: {e}")
            stats["errors"].append(f"Import error: {str(e)}")

        return stats

    async def import_odaily_articles(
        self,
        limit: int = 20,
        embed: bool = True,
        use_real: bool = False,
    ) -> dict:
        """将 Odaily 深度文章导入知识库。

        Args:
            limit: 最大导入文章数
            embed: 是否立即生成嵌入
            use_real: 是否获取真实文章（False = 使用模拟数据）

        Returns:
            包含导入统计信息的字典
        """
        logger.info(f"Starting Odaily deep articles import (limit: {limit}, use_real: {use_real})")

        stats = {
            "fetched": 0,
            "imported": 0,
            "embedded": 0,
            "failed": 0,
            "errors": [],
        }

        try:
            from app.wrappers.odaily import OdailyRestScraper

            # 使用 OdailyRestScraper 获取深度文章
            scraper = OdailyRestScraper()

            # 获取深度文章
            articles = await scraper.fetch_depth_articles(limit=limit)
            stats["fetched"] = len(articles)

            logger.info(f"Fetched {len(articles)} articles from Odaily deep")

            # 导入每篇文章
            for article in articles:
                try:
                    # 准备内容
                    content = article.content or ""

                    # 构建元数据
                    metadata = {
                        "source_id": article.id,
                        "published_at": article.publishDate,
                    }
                    if article.images:
                        metadata["images"] = article.images

                    # 保存到本地文件
                    self._save_to_local(
                        source="odaily",
                        doc_id=article.id or f"unknown_{hash(article.title)}",
                        title=article.title,
                        content=content,
                        url=article.sourceUrl,
                        metadata=metadata,
                    )

                    # 插入数据库
                    doc_id = await insert_document(
                        title=article.title,
                        content=content,
                        source_url=article.sourceUrl,
                        source_type="odaily-deep",
                        metadata=metadata,
                    )

                    logger.info(f"Imported article: {article.title} (doc_id: {doc_id})")
                    stats["imported"] += 1

                except Exception as e:
                    logger.error(f"Failed to import article {article.title}: {e}")
                    stats["failed"] += 1
                    stats["errors"].append(f"{article.title}: {str(e)}")

            # 如果请求则生成嵌入
            if embed and stats["imported"] > 0:
                stats["embedded"] = await self._embed_recent_documents(stats["imported"])

        except ImportError as e:
            logger.warning(f"Odaily scraper not available: {e}")
            stats["errors"].append(f"Odaily scraper not available: {str(e)}")
        except Exception as e:
            logger.error(f"Error during Odaily import: {e}")
            stats["errors"].append(f"Import error: {str(e)}")

        return stats

    async def import_document(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        source_type: str = "manual",
        metadata: Optional[dict] = None,
        embed: bool = True,
    ) -> int:
        """将单个文档导入知识库。

        Args:
            title: 文档标题
            content: 文档内容
            source_url: 可选的来源 URL
            source_type: 数据源类型标识
            metadata: 可选的元数据字典
            embed: 是否立即生成嵌入

        Returns:
            文档 ID
        """
        doc_id = await insert_document(
            title=title,
            content=content,
            source_url=source_url,
            source_type=source_type,
            metadata=metadata or {},
        )

        logger.info(f"Imported document: {title} (doc_id: {doc_id})")

        if embed:
            await self._embed_document(doc_id, content)

        return doc_id

    def _save_to_local(
        self,
        source: str,
        doc_id: str,
        title: str,
        content: str,
        url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Path:
        """将爬取的文档保存到本地存储。

        Args:
            source: 数据源类型（rootdata、odaily、tokenomics）
            doc_id: 唯一文档标识符
            title: 文档标题
            content: 文档内容
            url: 来源 URL
            metadata: 可选的元数据

        Returns:
            保存文件的路径
        """
        if not self.save_local:
            return None

        # 文件名安全化处理
        safe_title = title.replace("/", "-").replace("\\", "-")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{doc_id}_{timestamp}.json"

        filepath = KB_DOCS_DIR / source / filename

        # 准备数据
        data = {
            "source": source,
            "doc_id": doc_id,
            "scraped_at": datetime.now().isoformat(),
            "title": title,
            "content": content,
            "url": url,
            "metadata": metadata or {},
        }

        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved to local: {filepath}")
        return filepath

    async def _embed_document(self, doc_id: int, content: str) -> bool:
        """为文档生成嵌入向量。

        Args:
            doc_id: 文档 ID
            content: 文档内容

        Returns:
            成功返回 True
        """
        try:
            embedding_service = await self.get_embedding_service()

            # 将内容切分为块
            chunks = embedding_service._split_text(content, max_length=500)

            # 生成并存储嵌入
            for i, chunk in enumerate(chunks):
                await embedding_service.embed_and_store_chunk(
                    document_id=doc_id,
                    chunk_index=i,
                    content=chunk,
                )

            return True

        except Exception as e:
            logger.error(f"Error embedding document {doc_id}: {e}")
            return False

    async def _embed_recent_documents(self, count: int) -> int:
        """为最近添加的文档生成嵌入向量。

        Args:
            count: 要嵌入的最近文档数量

        Returns:
            已嵌入的文档数量
        """
        try:
            from app.data.vector import get_all_documents

            embedding_service = await self.get_embedding_service()
            documents = await get_all_documents(limit=count)

            embedded = 0
            for doc in documents:
                try:
                    if await self._embed_document(doc.id, doc.content):
                        embedded += 1
                except Exception as e:
                    logger.error(f"Error embedding doc {doc.id}: {e}")

            return embedded

        except Exception as e:
            logger.error(f"Error embedding recent documents: {e}")
            return 0

    async def import_tokenomics_docs(
        self,
        limit: int = 20,
        embed: bool = True,
    ) -> dict:
        """将代币经济学文档导入知识库。

        Args:
            limit: 最大导入文档数
            embed: 是否立即生成嵌入

        Returns:
            包含导入统计信息的字典
        """
        logger.info(f"Starting tokenomics import (limit: {limit})")

        stats = {
            "fetched": 0,
            "imported": 0,
            "embedded": 0,
            "failed": 0,
            "errors": [],
        }

        # 代币经济学文档将从 Rootdata 项目中提取
        # 这是一个调用 Rootdata 导入的封装
        try:
            project_stats = await self.import_rootdata_projects(limit=limit, embed=embed)
            stats.update(project_stats)
        except Exception as e:
            logger.error(f"Error during tokenomics import: {e}")
            stats["errors"].append(f"Import error: {str(e)}")

        return stats


# 全局实例
_loader: Optional[KnowledgeLoader] = None


def get_knowledge_loader() -> KnowledgeLoader:
    """获取全局知识库加载器实例。"""
    global _loader
    if _loader is None:
        _loader = KnowledgeLoader()
    return _loader
