import sys
from pathlib import Path

sys.path.insert(0, "tools")

import zenodo_upload_v112


SCRIPT = Path("tools/zenodo_upload_v112.py")


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class Session:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def post(self, url, json=None):
        self.calls.append(("post", url, json))
        if url.endswith("/actions/publish"):
            return Response(
                202,
                {
                    "id": 123,
                    "record_id": 456,
                    "state": "done",
                    "submitted": True,
                    "links": {"html": "https://zenodo.org/records/456"},
                    "metadata": {"title": "Title", "doi": "10.5281/zenodo.456"},
                },
            )
        return Response(
            201,
            {
                "id": 123,
                "links": {"bucket": "https://zenodo.org/api/files/bucket-id"},
            },
        )

    def get(self, url):
        self.calls.append(("get", url, None))
        return Response(
            200,
            {
                "id": 123,
                "links": {"bucket": "https://zenodo.org/api/files/bucket-id"},
            },
        )

    def put(self, url, data=None, json=None):
        self.calls.append(("put", url, json if json is not None else "data"))
        if url.endswith("/deposit/depositions/123"):
            return Response(
                200,
                {
                    "id": 123,
                    "record_id": 456,
                    "state": "unsubmitted",
                    "submitted": False,
                    "links": {"html": "https://zenodo.org/deposit/123"},
                    "metadata": json["metadata"],
                },
            )
        return Response(201, {"filename": zenodo_upload_v112.ASSET_NAME})


def test_dry_run_report_contains_package_and_metadata(tmp_path):
    zip_path = tmp_path / "package.zip"
    zip_path.write_bytes(b"abc")

    report = zenodo_upload_v112.dry_run_report(
        "https://zenodo.org/api",
        zip_path,
        Path("metadata.json"),
        {
            "title": "Title",
            "version": "v1.12",
            "notes": f"{zenodo_upload_v112.ZIP_SHA_NOTE_PREFIX}: digest",
        },
        deposition_id=None,
        publish=False,
    )

    assert report["mode"] == "dry-run"
    assert report["zip_size"] == 3
    assert report["zip_sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert report["title"] == "Title"
    assert report["metadata_notes_include_zip_sha"] is True
    assert report["would_publish"] is False


def test_checked_json_accepts_expected_status():
    payload = {"id": 123}

    assert zenodo_upload_v112.checked_json(Response(201, payload), {201}, "create") == payload


def test_checked_json_rejects_unexpected_status():
    try:
        zenodo_upload_v112.checked_json(Response(400, {"error": "bad"}), {201}, "create")
    except zenodo_upload_v112.ZenodoError as exc:
        assert "create failed with HTTP 400" in str(exc)
    else:
        raise AssertionError("expected ZenodoError")


def test_deposition_summary_prefers_links_and_doi():
    summary = zenodo_upload_v112.deposition_summary(
        {
            "id": 10,
            "record_id": 11,
            "state": "unsubmitted",
            "submitted": False,
            "links": {"html": "https://zenodo.org/deposit/10"},
            "metadata": {"title": "Title", "prereserve_doi": {"doi": "10.5072/zenodo.10"}},
        }
    )

    assert summary["id"] == 10
    assert summary["title"] == "Title"
    assert summary["doi"] == "10.5072/zenodo.10"


def test_sandbox_default_token_names_are_distinct_from_production():
    sandbox_names = zenodo_upload_v112.audit_zenodo_upload_readiness.SANDBOX_TOKEN_ENV_VARS

    assert "ZENODO_SANDBOX_ACCESS_TOKEN" in sandbox_names
    assert (
        sandbox_names != zenodo_upload_v112.audit_zenodo_upload_readiness.TOKEN_ENV_VARS
    )


def test_publish_help_mentions_deposition_id_requirement():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Publish after uploading. Requires --deposition-id." in text


def test_metadata_with_zip_sha_appends_non_circular_upload_note(tmp_path):
    zip_path = tmp_path / "package.zip"
    zip_path.write_bytes(b"abc")
    metadata = {"notes": "Existing note."}

    updated = zenodo_upload_v112.metadata_with_zip_sha(metadata, zip_path)

    assert metadata == {"notes": "Existing note."}
    assert "Existing note." in updated["notes"]
    assert zenodo_upload_v112.ZIP_SHA_NOTE_PREFIX in updated["notes"]
    assert "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" in updated["notes"]


def test_metadata_with_zip_sha_is_idempotent(tmp_path):
    zip_path = tmp_path / "package.zip"
    zip_path.write_bytes(b"abc")
    metadata = {
        "notes": (
            f"{zenodo_upload_v112.ZIP_SHA_NOTE_PREFIX}: "
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
    }

    assert zenodo_upload_v112.metadata_with_zip_sha(metadata, zip_path) == metadata


def test_write_json_result_prints_and_writes_same_payload(tmp_path):
    output_path = tmp_path / "result.json"
    rendered = zenodo_upload_v112.write_json_result({"mode": "draft", "id": 123}, output_path)

    assert '"id": 123' in rendered
    assert output_path.read_text(encoding="utf-8") == f"{rendered}\n"


def test_token_from_env_accepts_explicit_environment():
    token = zenodo_upload_v112.token_from_env(
        ["ZENODO_ACCESS_TOKEN"],
        environ={"ZENODO_ACCESS_TOKEN": "explicit-token"},
    )

    assert token == "explicit-token"


def test_upload_result_records_uploaded_zip_identity(tmp_path, monkeypatch):
    repo = tmp_path
    zip_path = repo / "package.zip"
    metadata_path = repo / "metadata.json"
    zip_path.write_bytes(b"abc")
    metadata_path.write_text('{"title":"Title","version":"v1.12","notes":"Note."}', encoding="utf-8")
    session = Session()

    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "secret-value")
    monkeypatch.setattr(
        zenodo_upload_v112.audit_zenodo_upload_readiness,
        "audit",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(zenodo_upload_v112.requests, "Session", lambda: session)

    result = zenodo_upload_v112.upload(
        repo_root=repo,
        api_base="https://zenodo.org/api",
        zip_path=zip_path,
        metadata_path=metadata_path,
        deposition_id=None,
        publish=False,
        dry_run=False,
        token_env=["ZENODO_ACCESS_TOKEN"],
    )

    assert result["mode"] == "draft"
    assert result["zip_sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert result["zip_size"] == 3
    assert result["metadata_notes_include_zip_sha"] is True
    assert session.headers["Authorization"] == "Bearer secret-value"


def test_upload_uses_known_local_env_tokens(tmp_path, monkeypatch):
    repo = tmp_path
    zip_path = repo / "package.zip"
    metadata_path = repo / "metadata.json"
    zip_path.write_bytes(b"abc")
    metadata_path.write_text('{"title":"Title","version":"v1.12","notes":"Note."}', encoding="utf-8")
    (repo / ".env").write_text("ZENODO_ACCESS_TOKEN=local-token\n", encoding="utf-8")
    session = Session()

    monkeypatch.delenv("ZENODO_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(
        zenodo_upload_v112.audit_zenodo_upload_readiness,
        "audit",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(zenodo_upload_v112.requests, "Session", lambda: session)

    result = zenodo_upload_v112.upload(
        repo_root=repo,
        api_base="https://zenodo.org/api",
        zip_path=zip_path,
        metadata_path=metadata_path,
        deposition_id=None,
        publish=False,
        dry_run=False,
        token_env=["ZENODO_ACCESS_TOKEN"],
    )

    assert result["mode"] == "draft"
    assert session.headers["Authorization"] == "Bearer local-token"


def test_published_upload_result_records_utc_timestamp(tmp_path, monkeypatch):
    repo = tmp_path
    zip_path = repo / "package.zip"
    metadata_path = repo / "metadata.json"
    zip_path.write_bytes(b"abc")
    metadata_path.write_text('{"title":"Title","version":"v1.12","notes":"Note."}', encoding="utf-8")
    session = Session()

    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "secret-value")
    monkeypatch.setattr(
        zenodo_upload_v112.audit_zenodo_upload_readiness,
        "audit",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(zenodo_upload_v112.requests, "Session", lambda: session)
    monkeypatch.setattr(zenodo_upload_v112, "utc_now_iso", lambda: "2026-07-20T10:30:00Z")

    result = zenodo_upload_v112.upload(
        repo_root=repo,
        api_base="https://zenodo.org/api",
        zip_path=zip_path,
        metadata_path=metadata_path,
        deposition_id="123",
        publish=True,
        dry_run=False,
        token_env=["ZENODO_ACCESS_TOKEN"],
    )

    assert result["mode"] == "published"
    assert result["published_at_utc"] == "2026-07-20T10:30:00Z"


def test_publish_requires_existing_deposition_id_before_network_calls(tmp_path, monkeypatch):
    repo = tmp_path
    zip_path = repo / "package.zip"
    metadata_path = repo / "metadata.json"
    zip_path.write_bytes(b"abc")
    metadata_path.write_text('{"title":"Title","version":"v1.12","notes":"Note."}', encoding="utf-8")
    session = Session()

    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "secret-value")
    monkeypatch.setattr(
        zenodo_upload_v112.audit_zenodo_upload_readiness,
        "audit",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(zenodo_upload_v112.requests, "Session", lambda: session)

    try:
        zenodo_upload_v112.upload(
            repo_root=repo,
            api_base="https://zenodo.org/api",
            zip_path=zip_path,
            metadata_path=metadata_path,
            deposition_id=None,
            publish=True,
            dry_run=False,
            token_env=["ZENODO_ACCESS_TOKEN"],
        )
    except zenodo_upload_v112.ZenodoError as exc:
        assert "publish requires --deposition-id" in str(exc)
    else:
        raise AssertionError("expected ZenodoError")

    assert session.calls == []
