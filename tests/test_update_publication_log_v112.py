import sys

sys.path.insert(0, "tools")

import update_publication_log_v112


VALID_SHA = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
POST_DOI_SHA = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"


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
        f"- Asset SHA-256: {VALID_SHA}",
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
        "asset_name": update_publication_log_v112.ASSET_NAME,
        "zip_sha256": VALID_SHA,
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
        zip_digest=VALID_SHA,
        sandbox=False,
    )

    assert "- Target commit: abc123" in updated
    assert f"- Asset SHA-256: {VALID_SHA}" in updated
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
        "asset_name": update_publication_log_v112.ASSET_NAME,
        "zip_sha256": VALID_SHA,
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
        zip_digest=POST_DOI_SHA,
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


def test_update_log_text_supports_full_publish_then_doi_commit_sequence():
    payload = {
        "mode": "published",
        "asset_name": update_publication_log_v112.ASSET_NAME,
        "zip_sha256": VALID_SHA,
        "published_at_utc": "2026-07-20T10:30:00Z",
        "deposition": {
            "id": 123,
            "record_id": 456,
            "html": "https://zenodo.org/records/456",
            "doi": "10.5281/zenodo.456",
        },
    }
    upload_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    doi_commit = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    after_publish = update_publication_log_v112.update_log_text(
        template(),
        payload,
        current_commit=upload_commit,
        zip_digest=VALID_SHA,
        sandbox=False,
    )
    after_doi_commit = update_publication_log_v112.update_log_text(
        after_publish,
        payload,
        current_commit=doi_commit,
        zip_digest=POST_DOI_SHA,
        sandbox=False,
        doi_update_commit=doi_commit,
    )

    assert f"- Target commit: {upload_commit}" in after_doi_commit
    assert f"- Asset SHA-256: {VALID_SHA}" in after_doi_commit
    assert f"- DOI metadata update commit: {doi_commit}" in after_doi_commit
    assert POST_DOI_SHA not in after_doi_commit


def test_update_log_text_repeated_publish_preserves_uploaded_identity():
    payload = {
        "mode": "published",
        "asset_name": update_publication_log_v112.ASSET_NAME,
        "zip_sha256": VALID_SHA,
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
        zip_digest=POST_DOI_SHA,
        sandbox=False,
    )

    assert "- Target commit: abcdef1234567890abcdef1234567890abcdef12" in updated
    assert f"- Asset SHA-256: {VALID_SHA}" in updated
    assert POST_DOI_SHA not in updated


def test_update_log_text_rejects_doi_metadata_commit_before_release_identity():
    try:
        update_publication_log_v112.update_log_text(
            template(),
            {
                "mode": "published",
                "asset_name": update_publication_log_v112.ASSET_NAME,
                "zip_sha256": VALID_SHA,
                "published_at_utc": "2026-07-20T10:30:00Z",
                "deposition": {
                    "id": 123,
                    "record_id": 456,
                    "html": "https://zenodo.org/records/456",
                    "doi": "10.5281/zenodo.456",
                },
            },
            current_commit="ffffffffffffffffffffffffffffffffffffffff",
            zip_digest=VALID_SHA,
            sandbox=False,
            doi_update_commit="1234567890abcdef1234567890abcdef12345678",
        )
    except ValueError as exc:
        assert "Zenodo-uploaded Target commit" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_update_log_text_fills_sandbox_only_when_requested():
    payload = {
        "mode": "draft",
        "asset_name": update_publication_log_v112.ASSET_NAME,
        "zip_sha256": VALID_SHA,
        "deposition": {"id": 999},
    }

    updated = update_publication_log_v112.update_log_text(
        template(),
        payload,
        current_commit="abc123",
        zip_digest=VALID_SHA,
        sandbox=True,
    )

    assert "- Sandbox deposition ID: 999" in updated
    assert "- Production deposition ID: TODO" in updated
    assert "- Target commit: TODO" in updated
    assert "- Asset SHA-256: TODO" in updated


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


def test_update_log_text_rejects_stale_zenodo_json_zip_sha():
    try:
        update_publication_log_v112.update_log_text(
            template(),
            {
                "mode": "draft",
                "asset_name": update_publication_log_v112.ASSET_NAME,
                "zip_sha256": "stale",
                "deposition": {"id": 123},
            },
            current_commit="abc123",
            zip_digest=VALID_SHA,
            sandbox=False,
        )
    except ValueError as exc:
        assert "does not match expected uploaded release zip" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_update_log_text_rejects_published_payload_without_doi():
    try:
        update_publication_log_v112.update_log_text(
            template(),
            {
                "mode": "published",
                "asset_name": update_publication_log_v112.ASSET_NAME,
                "zip_sha256": VALID_SHA,
                "published_at_utc": "2026-07-20T10:30:00Z",
                "deposition": {
                    "id": 123,
                    "record_id": 456,
                    "html": "https://zenodo.org/records/456",
                },
            },
            current_commit="abc123",
            zip_digest=VALID_SHA,
            sandbox=False,
        )
    except ValueError as exc:
        assert "does not include a production Zenodo DOI" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_update_log_text_rejects_historical_v1_doi_for_v112():
    try:
        update_publication_log_v112.update_log_text(
            template(),
            {
                "mode": "published",
                "asset_name": update_publication_log_v112.ASSET_NAME,
                "zip_sha256": VALID_SHA,
                "published_at_utc": "2026-07-20T10:30:00Z",
                "deposition": {
                    "id": 123,
                    "record_id": 21338004,
                    "html": "https://zenodo.org/records/21338004",
                    "doi": "10.5281/zenodo.21338004",
                },
            },
            current_commit="abc123",
            zip_digest=VALID_SHA,
            sandbox=False,
        )
    except ValueError as exc:
        assert "historical v1.0 DOI" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_update_log_text_rejects_doi_metadata_commit_with_mismatched_uploaded_sha():
    try:
        update_publication_log_v112.update_log_text(
            filled_release_identity_template(),
            {
                "mode": "published",
                "asset_name": update_publication_log_v112.ASSET_NAME,
                "zip_sha256": POST_DOI_SHA,
                "published_at_utc": "2026-07-20T10:30:00Z",
                "deposition": {
                    "id": 123,
                    "record_id": 456,
                    "html": "https://zenodo.org/records/456",
                    "doi": "10.5281/zenodo.456",
                },
            },
            current_commit="ffffffffffffffffffffffffffffffffffffffff",
            zip_digest=POST_DOI_SHA,
            sandbox=False,
            doi_update_commit="1234567890abcdef1234567890abcdef12345678",
        )
    except ValueError as exc:
        assert "does not match expected uploaded release zip" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_validate_commit_rejects_short_sha():
    try:
        update_publication_log_v112.validate_commit("abc123")
    except ValueError as exc:
        assert "40-character" in str(exc)
    else:
        raise AssertionError("expected ValueError")
