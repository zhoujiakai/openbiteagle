"""Knowledge base loader service.

This service orchestrates importing documents from various sources
into the RAG knowledge base.
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

# Base directory for storing scraped documents locally
KB_DOCS_DIR = Path(__file__).parent.parent.parent / "data" / "kb_docs"


class KnowledgeLoader:
    """Service for loading documents into the knowledge base."""

    def __init__(self, save_local: bool = True):
        """Initialize the knowledge loader.

        Args:
            save_local: Whether to save scraped documents to local files
        """
        self.embedding_service: Optional[EmbeddingService] = None
        self.save_local = save_local

        # Ensure local storage directories exist
        if self.save_local:
            for subdir in ["rootdata", "odaily", "tokenomics"]:
                (KB_DOCS_DIR / subdir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage ready: {KB_DOCS_DIR}")

    async def get_embedding_service(self) -> EmbeddingService:
        """Get or create the embedding service."""
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
        """Import projects from Rootdata into the knowledge base.

        Args:
            limit: Maximum number of projects to import
            embed: Whether to generate embeddings immediately
            import_to_kg: Whether to also import to Neo4j Knowledge Graph

        Returns:
            Dict with import statistics
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
            # Fetch projects from Rootdata
            projects = await scrape_rootdata_projects(limit=limit)
            stats["fetched"] = len(projects)

            logger.info(f"Fetched {len(projects)} projects from Rootdata")

            # Import to Neo4j KG first (if requested)
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

            # Import each project to RAG KB
            for project in projects:
                try:
                    # Convert to KB document format
                    doc_data = project.to_kb_document()

                    # Save to local file
                    self._save_to_local(
                        source="rootdata",
                        doc_id=project.rootdata_id,
                        title=doc_data["title"],
                        content=doc_data["content"],
                        url=doc_data.get("source_url"),
                        metadata=doc_data.get("metadata", {}),
                    )

                    # Insert into database
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

            # Generate embeddings if requested
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
        """Import deep articles from Odaily into the knowledge base.

        Args:
            limit: Maximum number of articles to import
            embed: Whether to generate embeddings immediately
            use_real: Whether to fetch real articles (False = use mock data)

        Returns:
            Dict with import statistics
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

            # Use OdailyRestScraper for in-depth articles
            scraper = OdailyRestScraper()

            # Fetch deep articles
            articles = await scraper.fetch_depth_articles(limit=limit)
            stats["fetched"] = len(articles)

            logger.info(f"Fetched {len(articles)} articles from Odaily deep")

            # Import each article
            for article in articles:
                try:
                    # Prepare content
                    content = article.content or ""

                    # Build metadata
                    metadata = {
                        "source_id": article.id,
                        "published_at": article.publishDate,
                    }
                    if article.images:
                        metadata["images"] = article.images

                    # Save to local file
                    self._save_to_local(
                        source="odaily",
                        doc_id=article.id or f"unknown_{hash(article.title)}",
                        title=article.title,
                        content=content,
                        url=article.sourceUrl,
                        metadata=metadata,
                    )

                    # Insert into database
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

            # Generate embeddings if requested
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
        """Import a single document into the knowledge base.

        Args:
            title: Document title
            content: Document content
            source_url: Optional source URL
            source_type: Source type identifier
            metadata: Optional metadata dictionary
            embed: Whether to generate embeddings immediately

        Returns:
            Document ID
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
        """Save a scraped document to local storage.

        Args:
            source: Source type (rootdata, odaily, tokenomics)
            doc_id: Unique document identifier
            title: Document title
            content: Document content
            url: Source URL
            metadata: Optional metadata

        Returns:
            Path to saved file
        """
        if not self.save_local:
            return None

        # Sanitize filename
        safe_title = title.replace("/", "-").replace("\\", "-")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{doc_id}_{timestamp}.json"

        filepath = KB_DOCS_DIR / source / filename

        # Prepare data
        data = {
            "source": source,
            "doc_id": doc_id,
            "scraped_at": datetime.now().isoformat(),
            "title": title,
            "content": content,
            "url": url,
            "metadata": metadata or {},
        }

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved to local: {filepath}")
        return filepath

    async def _embed_document(self, doc_id: int, content: str) -> bool:
        """Generate embeddings for a document.

        Args:
            doc_id: Document ID
            content: Document content

        Returns:
            True if successful
        """
        try:
            embedding_service = await self.get_embedding_service()

            # Split content into chunks
            chunks = embedding_service._split_text(content, max_length=500)

            # Generate and store embeddings
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
        """Generate embeddings for recently added documents.

        Args:
            count: Number of recent documents to embed

        Returns:
            Number of documents embedded
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
        """Import tokenomics documents into the knowledge base.

        Args:
            limit: Maximum number of documents to import
            embed: Whether to generate embeddings immediately

        Returns:
            Dict with import statistics
        """
        logger.info(f"Starting tokenomics import (limit: {limit})")

        stats = {
            "fetched": 0,
            "imported": 0,
            "embedded": 0,
            "failed": 0,
            "errors": [],
        }

        # Tokenomics docs will be extracted from Rootdata projects
        # This is a wrapper that calls the Rootdata import
        try:
            project_stats = await self.import_rootdata_projects(limit=limit, embed=embed)
            stats.update(project_stats)
        except Exception as e:
            logger.error(f"Error during tokenomics import: {e}")
            stats["errors"].append(f"Import error: {str(e)}")

        return stats


# Global instance
_loader: Optional[KnowledgeLoader] = None


def get_knowledge_loader() -> KnowledgeLoader:
    """Get the global knowledge loader instance."""
    global _loader
    if _loader is None:
        _loader = KnowledgeLoader()
    return _loader
