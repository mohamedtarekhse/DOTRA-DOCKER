import os
import uuid
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from ..config import settings


class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=False,
        )

    def _ensure_bucket(self, bucket: str):
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def save_image(self, bucket: str, data: bytes, ext: str = "jpg") -> str:
        self._ensure_bucket(bucket)
        key = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid.uuid4().hex}.{ext}"
        self.client.put_object(bucket, key, data, length=len(data), content_type=f"image/{ext}")
        return self.public_url(key)

    def public_url(self, key: str) -> str:
        return f"{settings.MINIO_PUBLIC_BASE}/{key}"

    def save_snapshot(self, data: bytes, ext: str = "jpg") -> str:
        return self.save_image("snapshots", data, ext)


storage = StorageService()
