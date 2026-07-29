from __future__ import annotations

from io import BytesIO

import pytest

from app.document_storage import DocumentStorageError, S3DocumentStorage


class FakeS3Client:
    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.calls: list[tuple[str, str, str]] = []

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str):
        assert ContentType == "application/octet-stream"
        self.objects[(Bucket, Key)] = Body
        self.calls.append(("put", Bucket, Key))
        return {"ETag": "test"}

    def get_object(self, *, Bucket: str, Key: str):
        self.calls.append(("get", Bucket, Key))
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, *, Bucket: str, Key: str):
        self.calls.append(("delete", Bucket, Key))
        self.objects.pop((Bucket, Key), None)
        return {}


def test_s3_backend_round_trip_uses_private_object_operations():
    client = FakeS3Client()
    storage = S3DocumentStorage(client, bucket="autopassport-private", prefix="documents")

    location = storage.write_atomic("vehicle-1/receipt.pdf", b"pdf-bytes")

    assert location == "documents/vehicle-1/receipt.pdf"
    assert storage.read("vehicle-1/receipt.pdf") == b"pdf-bytes"
    storage.delete("vehicle-1/receipt.pdf")
    assert ("autopassport-private", location) not in client.objects
    assert client.calls == [
        ("put", "autopassport-private", location),
        ("get", "autopassport-private", location),
        ("delete", "autopassport-private", location),
    ]


def test_s3_backend_rejects_unsafe_keys_before_client_call():
    client = FakeS3Client()
    storage = S3DocumentStorage(client, bucket="autopassport-private")

    for unsafe_key in ("", "../secret", "/absolute/file", "folder/../secret"):
        with pytest.raises(DocumentStorageError):
            storage.write_atomic(unsafe_key, b"data")

    assert client.calls == []


def test_s3_backend_requires_bucket_and_does_not_expose_local_path():
    client = FakeS3Client()

    with pytest.raises(DocumentStorageError, match="bucket"):
        S3DocumentStorage(client, bucket=" ")

    storage = S3DocumentStorage(client, bucket="autopassport-private")
    with pytest.raises(DocumentStorageError, match="local file paths"):
        storage.resolve("receipt.pdf")


def test_s3_backend_wraps_client_failures():
    class BrokenClient:
        def put_object(self, **kwargs):
            raise RuntimeError("network error")

        def get_object(self, **kwargs):
            raise RuntimeError("network error")

        def delete_object(self, **kwargs):
            raise RuntimeError("network error")

    storage = S3DocumentStorage(BrokenClient(), bucket="autopassport-private")

    with pytest.raises(DocumentStorageError, match="persist"):
        storage.write_atomic("receipt.pdf", b"data")
    with pytest.raises(DocumentStorageError, match="read"):
        storage.read("receipt.pdf")
    with pytest.raises(DocumentStorageError, match="delete"):
        storage.delete("receipt.pdf")
