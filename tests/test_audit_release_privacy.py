import sys

sys.path.insert(0, "tools")

import audit_release_privacy


def test_release_privacy_audit_accepts_clean_text(tmp_path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "README.md").write_text("Replicable public release package.\n")

    assert audit_release_privacy.audit_release(release_dir) == []


def test_release_privacy_audit_flags_token_shaped_text(tmp_path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "notes.txt").write_text(
        "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz123456\n"
    )

    findings = audit_release_privacy.audit_release(release_dir)

    assert any("token-shaped secret" in finding for finding in findings)


def test_release_privacy_audit_flags_local_paths(tmp_path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "config.txt").write_text(
        "source_path=/Users/example/private/raw.csv\n"
    )

    findings = audit_release_privacy.audit_release(release_dir)

    assert any("local path" in finding for finding in findings)


def test_release_privacy_audit_flags_private_file_names(tmp_path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "Umowa_private.pdf").write_bytes(b"%PDF")

    findings = audit_release_privacy.audit_release(release_dir)

    assert any("forbidden file name" in finding for finding in findings)
