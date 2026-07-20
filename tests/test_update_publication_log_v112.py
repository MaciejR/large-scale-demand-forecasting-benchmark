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
            "- Production DOI URL: TODO",
            "- Published at: TODO",
            "- DOI metadata update commit: TODO",
        ]
    ) + "\n"


def filled_release_identity_template():
    return template().replace(
        "- Target commit: TODO",
        "- Target commit: abcdef1234567890abcdef1234567890abcdef12",
    ).replace(
        "- Asset SHA-256: TODO",
        "- Asset SHA-256: "
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )


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
        "published_at_utc": "2026-07-20T10:30:00Z",
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
    assert "- Production DOI URL: https://doi.org/10.5281/zenodo.456" in updated
    assert "- Published at: 2026-07-20T10:30:00Z" in updated
    assert "- DOI metadata update commit: TODO" in updated


def test_update_log_text_records_doi_metadata_commit_without_overwriting_uploaded_identity():
    doi_update_commit = "1234567890abcdef1234567890abcdef12345678"
    payload = {
        "mode": "published",
        "published_at_utc": "2026-07-20T10:30:00Z",
        "deposition": {
            "id": 123,
            "record_id": 456,
            "html": "https://zenodo.org/records/456",
            "doi": "10.5281/zenodo.456",
        },
    }

    updated = update_publication_log_v112.update_log_text(
        filled_release_identity_template(),
        payload,
        current_commit="ffffffffffffffffffffffffffffffffffffffff",
        zip_digest="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        sandbox=False,
        doi_update_commit=doi_update_commit,
    )

    assert "- Target commit: abcdef1234567890abcdef1234567890abcdef12" in updated
    assert (
        "- Asset SHA-256: "
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        in updated
    )
    assert f"- DOI metadata update commit: {doi_update_commit}" in updated


def test_update_log_text_rejects_doi_metadata_commit_before_release_identity():
    try:
        update_publication_log_v112.update_log_text(
            template(),
            {"mode": "published"},
            current_commit="ffffffffffffffffffffffffffffffffffffffff",
            zip_digest="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            sandbox=False,
            doi_update_commit="1234567890abcdef1234567890abcdef12345678",
        )
    except ValueError as exc:
        assert "Zenodo-uploaded Target commit" in str(exc)
    else:
        raise AssertionError("expected ValueError")


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


def test_validate_commit_rejects_short_sha():
    try:
        update_publication_log_v112.validate_commit("abc123")
    except ValueError as exc:
        assert "40-character" in str(exc)
    else:
        raise AssertionError("expected ValueError")
