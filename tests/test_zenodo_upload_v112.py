import sys
from pathlib import Path

sys.path.insert(0, "tools")

import zenodo_upload_v112


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_dry_run_report_contains_package_and_metadata(tmp_path):
    zip_path = tmp_path / "package.zip"
    zip_path.write_bytes(b"abc")

    report = zenodo_upload_v112.dry_run_report(
        "https://zenodo.org/api",
        zip_path,
        Path("metadata.json"),
        {"title": "Title", "version": "v1.12"},
        deposition_id=None,
        publish=False,
    )

    assert report["mode"] == "dry-run"
    assert report["zip_size"] == 3
    assert report["title"] == "Title"
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
