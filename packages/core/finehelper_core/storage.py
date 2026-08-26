from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import boto3
from botocore.config import Config

from finehelper_core.settings import Settings


class ObjectStore(Protocol):
    def put(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def presign_put(self, key: str, expires: int = 3600, content_type: str = "application/octet-stream") -> str: ...
    def presign_get(self, key: str, expires: int = 3600) -> str: ...
    def uri(self, key: str) -> str: ...


class LocalObjectStore:
    def __init__(self, root: str, public_base: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base = public_base.rstrip("/")

    def _path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> str:
        self._path(key).write_bytes(body)
        return self.uri(key)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def presign_put(self, key: str, expires: int = 3600, content_type: str = "application/octet-stream") -> str:
        del expires, content_type
        return f"{self.public_base}/v1/internal/local-upload/{quote(key, safe='')}"

    def presign_get(self, key: str, expires: int = 3600) -> str:
        del expires
        return f"{self.public_base}/v1/internal/local-download/{quote(key, safe='')}"

    def uri(self, key: str) -> str:
        return f"local://{key}"


class S3ObjectStore:
    def __init__(self, settings: Settings):
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )

    def put(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)
        return self.uri(key)

    def get(self, key: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def presign_put(self, key: str, expires: int = 3600, content_type: str = "application/octet-stream") -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        )

    def presign_get(self, key: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def uri(self, key: str) -> str:
        return f"r2://{self.bucket}/{key}"


def object_key(*parts: str) -> str:
    return "/".join(str(p).strip("/") for p in parts if p is not None)


def guess_content_type(name: str) -> str:
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def build_store(settings: Settings) -> ObjectStore:
    if settings.uses_r2:
        return S3ObjectStore(settings)
    return LocalObjectStore(settings.local_storage_dir, settings.api_public_url)


def key_from_uri(uri: str) -> str:
    if uri.startswith("local://"):
        return uri[len("local://") :]
    if uri.startswith("r2://"):
        rest = uri[len("r2://") :]
        _bucket, _, key = rest.partition("/")
        return key
    return uri
