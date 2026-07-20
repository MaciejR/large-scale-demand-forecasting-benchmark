from pathlib import Path
import re


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
        "gh release edit v1.12 --target",
        "gh release upload v1.12 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip --clobber",
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
    release_edit_index = text.index("gh release edit v1.12 --target", build_index)
    release_upload_index = text.index("gh release upload v1.12", release_edit_index)
    public_audit_index = text.index(
        "python3 tools/audit_publication_readiness.py --require-public",
        release_upload_index,
    )
    log_update_index = text.index("--doi-update-commit", public_audit_index)

    assert (
        apply_index
        < dirty_check_index
        < clean_tree_note_index
        < build_index
        < release_edit_index
        < release_upload_index
        < public_audit_index
        < log_update_index
    )


def test_publication_handoff_reuploads_release_after_publication_log_update():
    text = Path("docs/PUBLICATION_HANDOFF_V1.12.md").read_text()

    log_update_commit_index = text.index("Commit and push the publication-log update")
    build_index = text.index("tools/build_v112_release.sh", log_update_commit_index)
    release_edit_index = text.index("gh release edit v1.12 --target", build_index)
    release_upload_index = text.index("gh release upload v1.12", release_edit_index)
    public_audit_index = text.index(
        "python3 tools/audit_publication_readiness.py --require-public",
        release_upload_index,
    )
    download_audit_index = text.index(
        "python3 tools/audit_github_release.py --verify-download",
        public_audit_index,
    )

    assert (
        log_update_commit_index
        < build_index
        < release_edit_index
        < release_upload_index
        < public_audit_index
        < download_audit_index
    )


def test_publication_handoff_records_json_for_direct_zenodo_uploads():
    text = Path("docs/PUBLICATION_HANDOFF_V1.12.md").read_text()

    required_commands = [
        (
            "python3 tools/zenodo_upload_v112.py --dry-run "
            "--output-json /tmp/zenodo-v1.12-dry-run.json"
        ),
        "python3 tools/zenodo_upload_v112.py --output-json /tmp/zenodo-v1.12-draft.json",
        (
            "python3 tools/zenodo_upload_v112.py --deposition-id <draft-id> "
            "--output-json /tmp/zenodo-v1.12-draft.json"
        ),
        (
            "python3 tools/zenodo_upload_v112.py --sandbox "
            "--output-json /tmp/zenodo-v1.12-sandbox.json"
        ),
    ]

    for command in required_commands:
        assert command in text

    bare_uploads = re.findall(r"^python3 tools/zenodo_upload_v112\\.py(?!.*--output-json).*$", text, re.M)
    assert bare_uploads == []
