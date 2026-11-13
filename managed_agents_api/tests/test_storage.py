"""Tests for the demo bucket setup."""

from managed_agents_demo import storage


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name
        self.size = None

    def upload_from_string(self, content, content_type=None):
        self.bucket.uploaded[self.name] = (content, content_type)
        self.size = len(content.encode())


class FakeBucket:
    def __init__(self, name):
        self.name = name
        self.uploaded = {}
        self.iam_configuration = type("Iam", (), {"uniform_bucket_level_access_enabled": False})()
        self.created_with = None

    def blob(self, name):
        return FakeBlob(self, name)


class FakeStorage:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = []
        self.project = "test-project"

    def lookup_bucket(self, name):
        return self.existing

    def bucket(self, name):
        return FakeBucket(name)

    def create_bucket(self, bucket, location=None, project=None):
        bucket.created_with = (location, project)
        self.created.append(bucket)
        return bucket


FILES = {"agent/AGENTS.md": "# a", "agent/data/sales.csv": "x,y\n1,2\n"}


def test_setup_creates_bucket_with_uniform_access_and_uploads():
    client = FakeStorage()
    result = storage.setup_bucket(client, "demo-bucket", "test-project", FILES)
    assert result.created is True
    bucket = client.created[0]
    assert bucket.created_with == ("US", "test-project")
    assert bucket.iam_configuration.uniform_bucket_level_access_enabled is True
    assert list(bucket.uploaded) == list(FILES)
    assert bucket.uploaded["agent/data/sales.csv"][1] == "text/csv"
    assert bucket.uploaded["agent/AGENTS.md"][1] == "text/markdown"
    assert result.uploaded == [("agent/AGENTS.md", 3), ("agent/data/sales.csv", 8)]


def test_setup_reuses_existing_bucket():
    existing = FakeBucket("demo-bucket")
    client = FakeStorage(existing=existing)
    result = storage.setup_bucket(client, "demo-bucket", "test-project", FILES)
    assert result.created is False
    assert client.created == []
    assert list(existing.uploaded) == list(FILES)


def test_console_url():
    assert storage.console_url("b", "agent/output/") == (
        "https://console.cloud.google.com/storage/browser/b/agent/output"
    )


class FakeDownloadBlob:
    def __init__(self, name, data):
        self.name = name
        self.size = len(data)
        self.data = data

    def download_to_filename(self, path):
        with open(path, "wb") as f:
            f.write(self.data)


class FakeListing:
    def __init__(self, blobs):
        self.blobs = blobs
        self.prefix = None

    def list_blobs(self, bucket, prefix=None):
        self.prefix = prefix
        return [blob for blob in self.blobs if blob.name.startswith(prefix)]


def test_download_output_writes_files_and_skips_folder(tmp_path):
    client = FakeListing(
        [
            FakeDownloadBlob("agent/output/", b""),
            FakeDownloadBlob("agent/output/report.md", b"# Report"),
            FakeDownloadBlob("agent/output/chart.png", b"PNG"),
        ]
    )
    files = storage.download_output(client, "b", "agent/output/", tmp_path)
    assert client.prefix == "agent/output/"
    assert [path.name for path, _ in files] == ["report.md", "chart.png"]
    assert (tmp_path / "report.md").read_bytes() == b"# Report"
    assert files[1][1] == 3
