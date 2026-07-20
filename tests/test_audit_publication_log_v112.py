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
        "- Target commit: 1234567890abcdef1234567890abcdef12345678\n"
        "- Asset SHA-256: "
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\n"
        "- Production DOI: 10.5281/zenodo.99999999\n"
        "- Production DOI URL: https://doi.org/10.5281/zenodo.99999999\n"
        "- Production record URL: https://zenodo.org/records/99999999\n"
        "- Published at: 2026-07-20T10:30:00Z\n"
        "- DOI metadata update commit: 1234567890abcdef1234567890abcdef12345678\n"
        "- Final package SHA-256 after DOI update: external GitHub release asset digest\n"
        "- Final GitHub release target after DOI update: external GitHub release targetCommitish"
    )

    assert audit_publication_log_v112.audit_complete_log_text(text) == []


def test_complete_publication_log_flags_mismatched_doi_url_and_short_commit():
    text = (
        "- Target commit: abc123\n"
        "- Asset SHA-256: deadbeef\n"
        "- Production DOI: 10.5281/zenodo.99999999\n"
        "- Production DOI URL: https://doi.org/10.5281/zenodo.11111111\n"
        "- Production record URL: https://zenodo.org/records/99999999\n"
        "- Published at: recorded by Zenodo\n"
        "- DOI metadata update commit: 123abc\n"
        "- Final package SHA-256 after DOI update: stale\n"
        "- Final GitHub release target after DOI update: stale"
    )

    findings = audit_publication_log_v112.audit_complete_log_text(text)

    assert any("Production DOI URL" in finding for finding in findings)
    assert (
        "publication log DOI metadata update commit is not a full 40-character git SHA"
        in findings
    )
    assert "publication log Published at is not an ISO-8601 UTC timestamp" in findings
    assert any("Final package SHA-256" in finding for finding in findings)
    assert any("Final GitHub release target" in finding for finding in findings)


def test_complete_publication_log_rejects_historical_v1_doi():
    text = (
        "- Target commit: 1234567890abcdef1234567890abcdef12345678\n"
        "- Asset SHA-256: "
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\n"
        "- Production DOI: 10.5281/zenodo.21338004\n"
        "- Production DOI URL: https://doi.org/10.5281/zenodo.21338004\n"
        "- Production record URL: https://zenodo.org/records/21338004\n"
        "- Published at: 2026-07-20T10:30:00Z\n"
        "- DOI metadata update commit: 1234567890abcdef1234567890abcdef12345678\n"
        "- Final package SHA-256 after DOI update: external GitHub release asset digest\n"
        "- Final GitHub release target after DOI update: external GitHub release targetCommitish"
    )

    findings = audit_publication_log_v112.audit_complete_log_text(text)

    assert "publication log uses the historical v1.0 DOI as the v1.12 DOI" in findings


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


def test_publication_log_audit_accepts_unpacked_release_context(tmp_path):
    replication = tmp_path / "replication"
    docs = replication / "docs"
    docs.mkdir(parents=True)
    (tmp_path / "COMMIT.txt").write_text("commit-a\n", encoding="utf-8")
    (tmp_path / "CHECKSUMS.txt").write_text("checksum placeholder\n", encoding="utf-8")
    (docs / "PUBLICATION_LOG_V1.12.md").write_text(
        "\n".join(
            [
                audit_publication_log_v112.GITHUB_RELEASE_URL,
                audit_publication_log_v112.ASSET_NAME,
                "- Target commit: commit-a",
                "- Asset SHA-256: TODO",
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

    assert audit_publication_log_v112.audit(replication, require_complete=False) == []


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


def test_complete_publication_log_allows_uploaded_release_identity_to_differ_from_final_package(tmp_path):
    repo = tmp_path
    log = repo / audit_publication_log_v112.LOG_PATH
    release_dir = repo / audit_publication_log_v112.RELEASE_DIR
    zip_path = repo / audit_publication_log_v112.ZIP_PATH
    log.parent.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    (release_dir / "COMMIT.txt").write_text(
        "ffffffffffffffffffffffffffffffffffffffff\n", encoding="utf-8"
    )
    zip_path.write_bytes(b"final package")

    log.write_text(
        "\n".join(
            [
                audit_publication_log_v112.GITHUB_RELEASE_URL,
                audit_publication_log_v112.ASSET_NAME,
                "- Target commit: 1234567890abcdef1234567890abcdef12345678",
                "- Asset SHA-256: "
                "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "- Production deposition ID: 123",
                "- Production record URL: https://zenodo.org/records/99999999",
                "- Production DOI: 10.5281/zenodo.99999999",
                "- Production DOI URL: https://doi.org/10.5281/zenodo.99999999",
                "- Published at: 2026-07-20T10:30:00Z",
                "- DOI metadata update commit: abcdef1234567890abcdef1234567890abcdef12",
                "- Final package SHA-256 after DOI update: external GitHub release asset digest",
                "- Final GitHub release target after DOI update: external GitHub release targetCommitish",
            ]
        ),
        encoding="utf-8",
    )

    assert audit_publication_log_v112.audit(repo, require_complete=True) == []


def test_complete_publication_log_flags_malformed_uploaded_release_identity(tmp_path):
    repo = tmp_path
    log = repo / audit_publication_log_v112.LOG_PATH
    release_dir = repo / audit_publication_log_v112.RELEASE_DIR
    zip_path = repo / audit_publication_log_v112.ZIP_PATH
    log.parent.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    (release_dir / "COMMIT.txt").write_text(
        "ffffffffffffffffffffffffffffffffffffffff\n", encoding="utf-8"
    )
    zip_path.write_bytes(b"final package")

    log.write_text(
        "\n".join(
            [
                audit_publication_log_v112.GITHUB_RELEASE_URL,
                audit_publication_log_v112.ASSET_NAME,
                "- Target commit: abc123",
                "- Asset SHA-256: deadbeef",
                "- Production deposition ID: 123",
                "- Production record URL: https://zenodo.org/records/99999999",
                "- Production DOI: 10.5281/zenodo.99999999",
                "- Production DOI URL: https://doi.org/10.5281/zenodo.99999999",
                "- Published at: 2026-07-20T10:30:00Z",
                "- DOI metadata update commit: abcdef1234567890abcdef1234567890abcdef12",
                "- Final package SHA-256 after DOI update: external GitHub release asset digest",
                "- Final GitHub release target after DOI update: external GitHub release targetCommitish",
            ]
        ),
        encoding="utf-8",
    )

    findings = audit_publication_log_v112.audit(repo, require_complete=True)

    assert "publication log Target commit is not a full 40-character git SHA" in findings
    assert "publication log Asset SHA-256 is not a 64-character SHA-256" in findings
