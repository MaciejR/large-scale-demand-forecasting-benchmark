from pathlib import Path


def test_release_build_runs_unpacked_zip_audit_after_zip_integrity_check():
    text = Path("tools/build_v112_release.sh").read_text(encoding="utf-8")

    zip_test_index = text.index('unzip -t "$zip_path"')
    unpacked_audit_index = text.index('python3 tools/audit_unpacked_release.py "$zip_path"')
    privacy_audit_index = text.index('python3 tools/audit_release_privacy.py "$release_dir"')

    assert zip_test_index < unpacked_audit_index < privacy_audit_index
