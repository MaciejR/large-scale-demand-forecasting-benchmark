from pathlib import Path


def test_publication_handoff_contains_finalization_commands():
    text = Path("docs/PUBLICATION_HANDOFF_V1.12.md").read_text()

    required = [
        "tools/build_v112_release.sh",
        "python3 tools/audit_publication_readiness.py",
        "python3 tools/audit_publication_readiness.py --require-public",
        "python3 tools/audit_github_release.py --verify-download",
        "python3 tools/audit_publication_log_v112.py",
        "tools/publish_v112_zenodo.sh dry-run",
        "tools/publish_v112_zenodo.sh publish --deposition-id",
        "replace the GitHub release asset",
        "release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip",
        "shasum -a 256 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip",
    ]

    for phrase in required:
        assert phrase in text


def test_readme_points_to_publication_handoff():
    readme = Path("README.md").read_text()

    assert "docs/PUBLICATION_HANDOFF_V1.12.md" in readme


def test_publication_handoff_builds_release_only_after_doi_metadata_commit():
    text = Path("docs/PUBLICATION_HANDOFF_V1.12.md").read_text()

    apply_index = text.index("python3 tools/apply_v112_zenodo_doi.py --doi")
    dirty_check_index = text.index("git diff --check", apply_index)
    clean_tree_note_index = text.index("The release builder requires a clean", dirty_check_index)
    build_index = text.index("tools/build_v112_release.sh", clean_tree_note_index)
    log_update_index = text.index("--doi-update-commit", build_index)

    assert apply_index < dirty_check_index < clean_tree_note_index < build_index < log_update_index
