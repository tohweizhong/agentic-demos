"""The demo bucket: create it and upload the agent files."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LOCATION = "US"

_CONTENT_TYPES = {".md": "text/markdown", ".csv": "text/csv"}


@dataclass
class SetupResult:
    """The result of `setup_bucket`."""

    bucket: str
    created: bool
    uploaded: list[tuple[str, int]] = field(default_factory=list)


def _content_type(name: str) -> str:
    for suffix, content_type in _CONTENT_TYPES.items():
        if name.endswith(suffix):
            return content_type
    return "text/plain"


def setup_bucket(
    storage_client: Any,
    bucket_name: str,
    project: str,
    files: dict[str, str],
    location: str = LOCATION,
) -> SetupResult:
    """Create the bucket if it does not exist, and upload the files.

    A new bucket uses uniform bucket-level access. The function does not change
    the settings of a bucket that exists.
    """
    bucket = storage_client.lookup_bucket(bucket_name)
    created = False
    if bucket is None:
        bucket = storage_client.bucket(bucket_name)
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        bucket = storage_client.create_bucket(bucket, location=location, project=project)
        created = True
    result = SetupResult(bucket=bucket_name, created=created)
    for name, content in files.items():
        blob = bucket.blob(name)
        blob.upload_from_string(content, content_type=_content_type(name))
        result.uploaded.append((name, len(content.encode("utf-8"))))
    return result


def console_url(bucket: str, prefix: str = "") -> str:
    """Return the Cloud console link to a bucket folder."""
    path = f"{bucket}/{prefix}".rstrip("/")
    return f"https://console.cloud.google.com/storage/browser/{path}"


def make_storage_client(project: str) -> Any:
    """Return a Cloud Storage client that uses Application Default Credentials."""
    from google.cloud import storage

    return storage.Client(project=project)
