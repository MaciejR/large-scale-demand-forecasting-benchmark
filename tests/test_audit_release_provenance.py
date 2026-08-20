import sys
from pathlib import Path

sys.path.insert(0, "tools")

import audit_release_provenance
import audit_v121_release


def test_current_release_static_metadata_is_consistent():
    repo_root = Path(".").resolve()
    assert audit_v121_release.audit_static(repo_root) == []


def test_v121_hygiene_rejects_raw_data_and_token_shaped_secrets(tmp_path):
    raw = tmp_path / "replication/data/raw"
    raw.mkdir(parents=True)
    (raw / "sample.csv").write_text("value\n1\n")
    (tmp_path / "credentials.txt").write_text(
        "token=" + "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"
    )
    findings = audit_v121_release.audit_package_hygiene(tmp_path)
    assert any("raw data included" in finding for finding in findings)
    assert any("token-shaped secret" in finding for finding in findings)


def test_release_provenance_accepts_post_doi_citation_metadata():
    text = (
        'version: "v1.12"\n'
        'date-released: "2026-07-20"\n'
        'doi: "10.5281/zenodo.99999999"\n'
        'url: "https://doi.org/10.5281/zenodo.99999999"\n'
        'repository-code: "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark"\n'
    )

    assert audit_release_provenance.audit_citation_text(text) == []


def test_release_provenance_flags_citation_without_release_or_doi_url():
    text = (
        'version: "v1.12"\n'
        'date-released: "2026-07-20"\n'
        'repository-code: "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark"\n'
    )

    findings = audit_release_provenance.audit_citation_text(text)

    assert any("missing GitHub release URL or minted Zenodo DOI" in finding for finding in findings)


def test_release_provenance_flags_commit_mismatch(tmp_path):
    release_dir = tmp_path / audit_release_provenance.RELEASE_STEM
    manuscript_dir = release_dir / "manuscript"
    docs_dir = release_dir / "replication/docs"
    manuscript_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    (release_dir / "COMMIT.txt").write_text("deadbeef\n")
    Path(f"{release_dir}.zip").write_text("zip placeholder\n")
    (manuscript_dir / audit_release_provenance.PDF_NAME).write_text("pdf placeholder\n")
    release_note = (
        f"`{audit_release_provenance.ZIP_PATH}`\n"
        f"- `manuscript/{audit_release_provenance.PDF_NAME}`\n"
    )
    (release_dir / "README.md").write_text(release_note)
    (docs_dir / "RELEASE_V1.12.md").write_text(release_note)

    findings = audit_release_provenance.audit_release_dir(
        Path(".").resolve(),
        release_dir,
        expected_head="cafebabe",
    )

    assert any("COMMIT.txt=deadbeef, expected HEAD=cafebabe" in finding for finding in findings)


def test_release_provenance_accepts_minimal_matching_release(tmp_path):
    release_dir = tmp_path / audit_release_provenance.RELEASE_STEM
    manuscript_dir = release_dir / "manuscript"
    docs_dir = release_dir / "replication/docs"
    manuscript_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    expected_head = "cafebabe"
    (release_dir / "COMMIT.txt").write_text(f"{expected_head}\n")
    Path(f"{release_dir}.zip").write_text("zip placeholder\n")
    (manuscript_dir / audit_release_provenance.PDF_NAME).write_text("pdf placeholder\n")
    release_note = (
        f"`{audit_release_provenance.ZIP_PATH}`\n"
        f"- `manuscript/{audit_release_provenance.PDF_NAME}`\n"
    )
    (release_dir / "README.md").write_text(release_note)
    (docs_dir / "RELEASE_V1.12.md").write_text(release_note)

    assert audit_release_provenance.audit_release_dir(
        Path(".").resolve(),
        release_dir,
        expected_head=expected_head,
    ) == []


def test_release_provenance_accepts_unpacked_release_without_outer_zip(tmp_path):
    release_dir = tmp_path / audit_release_provenance.RELEASE_STEM
    manuscript_dir = release_dir / "manuscript"
    docs_dir = release_dir / "replication/docs"
    manuscript_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    expected_head = "cafebabe"
    (release_dir / "COMMIT.txt").write_text(f"{expected_head}\n")
    (release_dir / "CHECKSUMS.txt").write_text("checksum placeholder\n")
    (manuscript_dir / audit_release_provenance.PDF_NAME).write_text("pdf placeholder\n")
    release_note = (
        f"`{audit_release_provenance.ZIP_PATH}`\n"
        f"- `manuscript/{audit_release_provenance.PDF_NAME}`\n"
    )
    (release_dir / "README.md").write_text(release_note)
    (docs_dir / "RELEASE_V1.12.md").write_text(release_note)

    assert audit_release_provenance.audit_release_dir(
        tmp_path,
        release_dir,
        expected_head=expected_head,
    ) == []


def test_release_provenance_reads_commit_from_unpacked_release_parent(tmp_path):
    replication = tmp_path / "replication"
    replication.mkdir()
    (tmp_path / "COMMIT.txt").write_text("cafebabe\n", encoding="utf-8")

    assert audit_release_provenance.current_git_head(replication) == "cafebabe"
