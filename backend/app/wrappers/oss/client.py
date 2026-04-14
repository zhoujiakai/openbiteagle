"""阿里云 OSS 对象存储客户端。

提供文件上传、下载、删除、预签名 URL 等功能。
"""

from typing import Any, BinaryIO

import oss2

from app.core.config import cfg
from data import create_logger

logger = create_logger("阿里云OSS文件存储")


class OSSClient:
    """阿里云 OSS 客户端。

    通过 oss2 SDK 访问 OSS，支持常见的文件操作。
    """

    def __init__(
        self,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        endpoint: str | None = None,
        bucket_name: str | None = None,
    ):
        """初始化 OSS 客户端。

        Args:
            access_key_id: 阿里云 AccessKey ID（默认从 cfg.oss 读取）
            access_key_secret: 阿里云 AccessKey Secret（默认从 cfg.oss 读取）
            endpoint: OSS Endpoint（默认从 cfg.oss 读取）
            bucket_name: Bucket 名称（默认从 cfg.oss 读取）
        """
        self.access_key_id = access_key_id or cfg.oss.OSS_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or cfg.oss.OSS_ACCESS_KEY_SECRET
        self.endpoint = endpoint or cfg.oss.OSS_ENDPOINT
        self.bucket_name = bucket_name or cfg.oss.OSS_BUCKET_NAME

        self._auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self._bucket = oss2.Bucket(self._auth, self.endpoint, self.bucket_name)

    def upload_file(
        self,
        key: str,
        data: bytes | BinaryIO | str,
        content_type: str | None = None,
    ) -> str:
        """上传文件到 OSS。

        Args:
            key: 对象存储路径（如 "images/photo.png"）
            data: 文件内容（bytes 或文件对象）
            content_type: MIME 类型（如 "image/png"）

        Returns:
            上传后的对象 key
        """
        try:
            headers: dict[str, str] = {}
            if content_type:
                headers["Content-Type"] = content_type

            if isinstance(data, (bytes, str)):
                self._bucket.put_object(key, data, headers=headers)
            else:
                self._bucket.put_object(key, data.read(), headers=headers)

            logger.info(f"上传文件成功: {key}")
            return key
        except oss2.exceptions.OssError as e:
            logger.error(f"上传文件失败: {key}, 错误: {e}")
            raise

    def download_file(self, key: str) -> bytes:
        """从 OSS 下载文件。

        Args:
            key: 对象存储路径

        Returns:
            文件内容的 bytes
        """
        try:
            result = self._bucket.get_object(key)
            data = result.read()
            logger.info(f"下载文件成功: {key}, 大小: {len(data)} bytes")
            return data
        except oss2.exceptions.OssError as e:
            logger.error(f"下载文件失败: {key}, 错误: {e}")
            raise

    def delete_file(self, key: str) -> None:
        """删除 OSS 上的文件。

        Args:
            key: 对象存储路径
        """
        try:
            self._bucket.delete_object(key)
            logger.info(f"删除文件成功: {key}")
        except oss2.exceptions.OssError as e:
            logger.error(f"删除文件失败: {key}, 错误: {e}")
            raise

    def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        """生成预签名 URL（临时访问链接）。

        Args:
            key: 对象存储路径
            expires: URL 有效期（秒），默认 1 小时

        Returns:
            预签名 URL 字符串
        """
        try:
            url = self._bucket.sign_url("GET", key, expires)
            logger.info(f"生成预签名URL: {key}, 有效期: {expires}秒")
            return url
        except oss2.exceptions.OssError as e:
            logger.error(f"生成预签名URL失败: {key}, 错误: {e}")
            raise

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict[str, Any]]:
        """列举 OSS 文件。

        Args:
            prefix: 路径前缀（如 "images/"）
            max_keys: 最大返回数量

        Returns:
            文件信息列表，每项包含 key 和 size 等字段
        """
        try:
            files: list[dict[str, Any]] = []
            for obj in oss2.ObjectIterator(self._bucket, prefix=prefix, max_keys=max_keys):
                files.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })
            logger.info(f"列举文件完成: prefix={prefix}, 数量: {len(files)}")
            return files
        except oss2.exceptions.OssError as e:
            logger.error(f"列举文件失败: prefix={prefix}, 错误: {e}")
            raise

    def file_exists(self, key: str) -> bool:
        """检查文件是否存在。

        Args:
            key: 对象存储路径

        Returns:
            文件是否存在
        """
        try:
            return self._bucket.object_exists(key)
        except oss2.exceptions.OssError as e:
            logger.error(f"检查文件存在性失败: {key}, 错误: {e}")
            raise

    def get_file_url(self, key: str) -> str:
        """获取文件的公开访问 URL。

        注意：Bucket 需要设置为公开读权限，否则返回的 URL 无法直接访问。
        如需临时访问，请使用 generate_presigned_url。

        Args:
            key: 对象存储路径

        Returns:
            文件的 URL
        """
        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    def health_check(self) -> bool:
        """健康检查：验证 Bucket 是否可访问。

        Returns:
            Bucket 是否可正常访问
        """
        try:
            self._bucket.get_bucket_info()
            return True
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS 健康检查失败: {e}")
            return False

    def close(self) -> None:
        """清理资源。

        oss2 SDK 无持久连接，此方法保留接口一致性。
        """
        pass
