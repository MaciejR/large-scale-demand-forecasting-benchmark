import sys

sys.path.insert(0, "tools")

import audit_publication_log_v112


def valid_log():
    return "\n".join(
        [
            audit_publication_log_v112.GITHUB_RELEASE_URL,
            audit_publication_log_v112.ASSET_NAME,
            "Target commit: TODO",
            "Asset SHA-256: TODO",
            "Production deposition ID: TODO",
            "Production record URL: TODO",
            "Production DOI: TODO",
            "Production DOI URL: TODO",
            "Published at: TODO",
            "DOI metadata update commit: TODO",
            "Final package SHA-256 after DOI update: TODO",
            "Final GitHub release target after DOI update: TODO",
        ]
    )


def test_publication_log_accepts_required_template_fields():
    assert audit_publication_log_v112.audit_log_text(valid_log()) == []


def test_publication_log_flags_missing_field():
    findings = audit_publication_log_v112.audit_log_text(
        valid_log().replace("Asset SHA-256: TODO", "")
    )

    assert findings == ["publication log missing field: Asset SHA-256:"]


def test_complete_publication_log_flags_todo_and_missing_doi():
    findings = audit_publication_log_v112.audit_complete_log_text("Production DOI: TODO")

    assert "publication log still contains TODO placeholders" in findings
    assert "publication log does not contain a Zenodo DOI" in findings
    assert "publication log does not contain a production DOI URL" in findings
    assert "publication log does not contain a production record URL" in findings
    assert "publication log Published at is not an ISO-8601 UTC timestamp" in findings
    assert (
        "publication log DOI metadata update commit is not a full 40-character git SHA"
        in findings
    )


def test_complete_publication_log_accepts_doi_record_and_no_todo():
    text = (
        "- Production DOI: 10.5281/zenodo.99999999\n"
        "- Production DOI URL: https://doi.org/10.5281/zenodo.99999999\n"
        "- Production record URL: https://zenodo.org/records/99999999\n"
        "- Published at: 2026-07-20T10:30:00Z\n"
        "- DOI metadata update commit: 1234567890abcdef1234567890abcdef12345678"
    )

    assert audit_publication_log_v112.audit_complete_log_text(text) == []


def test_complete_publication_log_flags_mismatched_doi_url_and_short_commit():
    text = (
        "- Production DOI: 10.5281/zenodo.99999999\n"
        "- Production DOI URL: https://doi.org/10.5281/zenodo.11111111\n"
        "- Production record URL: https://zenodo.org/records/99999999\n"
        "- Published at: recorded by Zenodo\n"
        "- DOI metadata update commit: 123abc"
    )

    findings = audit_publication_log_v112.audit_complete_log_text(text)

    assert any("Production DOI URL" in finding for finding in findings)
    assert (
        "publication log DOI metadata update commit is not a full 40-character git SHA"
        in findings
    )
    assert "publication log Published at is not an ISO-8601 UTC timestamp" in findings


def test_publication_log_checks_known_commit_and_sha_against_package(tmp_path):
    repo = tmp_path
    log = repo / audit_publication_log_v112.LOG_PATH
    release_dir = repo / audit_publication_log_v112.RELEASE_DIR
    zip_path = repo / audit_publication_log_v112.ZIP_PATH
    log.parent.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    (release_dir / "COMMIT.txt").write_text("commit-a\n", encoding="utf-8")
    zip_path.write_bytes(b"zip")
    digest = audit_publication_log_v112.sha256(zip_path)

    log.write_text(
        "\n".join(
            [
                audit_publication_log_v112.GITHUB_RELEASE_URL,
                audit_publication_log_v112.ASSET_NAME,
                "- Target commit: commit-a",
                f"- Asset SHA-256: {digest}",
                "- Production deposition ID: TODO",
                "- Production record URL: TODO",
                "- Production DOI: TODO",
                "- Production DOI URL: TODO",
                "- Published at: TODO",
                "- DOI metadata update commit: TODO",
                "- Final package SHA-256 after DOI update: TODO",
                "- Final GitHub release target after DOI update: TODO",
            ]
        ),
        encoding="utf-8",
    )

    assert audit_publication_log_v112.audit(repo, require_complete=False) == []


def test_publication_log_flags_stale_known_commit_and_sha(tmp_path):
    repo = tmp_path
    log = repo / audit_publication_log_v112.LOG_PATH
    release_dir = repo / audit_publication_log_v112.RELEASE_DIR
    zip_path = repo / audit_publication_log_v112.ZIP_PATH
    log.parent.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    (release_dir / "COMMIT.txt").write_text("commit-b\n", encoding="utf-8")
    zip_path.write_bytes(b"zip")

    log.write_text(
        "\n".join(
            [
                audit_publication_log_v112.GITHUB_RELEASE_URL,
                audit_publication_log_v112.ASSET_NAME,
                "- Target commit: commit-a",
                "- Asset SHA-256: stale",
                "- Production deposition ID: TODO",
                "- Production record URL: TODO",
                "- Production DOI: TODO",
                "- Production DOI URL: TODO",
                "- Published at: TODO",
                "- DOI metadata update commit: TODO",
                "- Final package SHA-256 after DOI update: TODO",
                "- Final GitHub release target after DOI update: TODO",
            ]
        ),
        encoding="utf-8",
    )

    findings = audit_publication_log_v112.audit(repo, require_complete=False)

    assert any("Target commit commit-a does not match" in finding for finding in findings)
    assert any("Asset SHA-256 stale does not match" in finding for finding in findings)
