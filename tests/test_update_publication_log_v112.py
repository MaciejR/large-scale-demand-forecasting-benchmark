import sys

sys.path.insert(0, "tools")

import update_publication_log_v112


def template():
    return "\n".join(
        [
            "- Target commit: TODO",
            "- Asset SHA-256: TODO",
            "- Sandbox deposition ID: TODO",
            "- Production deposition ID: TODO",
            "- Production record URL: TODO",
            "- Production DOI: TODO",
            "- Published at: TODO",
        ]
    ) + "\n"


def test_set_field_updates_exactly_one_markdown_field():
    updated = update_publication_log_v112.set_field("- Target commit: TODO\n", "Target commit", "abc")

    assert updated == "- Target commit: abc\n"


def test_set_field_rejects_missing_field():
    try:
        update_publication_log_v112.set_field("- Other: TODO\n", "Target commit", "abc")
    except ValueError as exc:
        assert "Target commit" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_update_log_text_fills_production_publish_result():
    payload = {
        "mode": "published",
        "deposition": {
            "id": 123,
            "record_id": 456,
            "html": "https://zenodo.org/records/456",
            "doi": "10.5281/zenodo.456",
        },
    }

    updated = update_publication_log_v112.update_log_text(
        template(),
        payload,
        current_commit="abc123",
        zip_digest="deadbeef",
        sandbox=False,
    )

    assert "- Target commit: abc123" in updated
    assert "- Asset SHA-256: deadbeef" in updated
    assert "- Production deposition ID: 123" in updated
    assert "- Production record URL: https://zenodo.org/records/456" in updated
    assert "- Production DOI: 10.5281/zenodo.456" in updated
    assert "- Published at: recorded by Zenodo" in updated


def test_update_log_text_fills_sandbox_only_when_requested():
    payload = {"mode": "draft", "deposition": {"id": 999}}

    updated = update_publication_log_v112.update_log_text(
        template(),
        payload,
        current_commit="abc123",
        zip_digest="deadbeef",
        sandbox=True,
    )

    assert "- Sandbox deposition ID: 999" in updated
    assert "- Production deposition ID: TODO" in updated


def test_update_log_text_dry_run_leaves_release_identity_placeholders():
    updated = update_publication_log_v112.update_log_text(
        template(),
        {"mode": "dry-run"},
        current_commit="abc123",
        zip_digest="deadbeef",
        sandbox=False,
    )

    assert "- Target commit: TODO" in updated
    assert "- Asset SHA-256: TODO" in updated
