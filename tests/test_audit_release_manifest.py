import sys

sys.path.insert(0, "tools")

import audit_release_manifest


def create_minimal_release(root):
    for rel_path in audit_release_manifest.REQUIRED_FILES:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n")

    latex_dir = root / "replication/paper/latex"
    latex_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(1, 10):
        (latex_dir / f"section{idx}.tex").write_text("section\n")
    for suffix in "abcdefg":
        (latex_dir / f"appendix_{suffix}.tex").write_text("appendix\n")

    tests_dir = root / "replication/tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(10):
        (tests_dir / f"test_{idx}.py").write_text("def test_placeholder():\n    assert True\n")


def test_release_manifest_accepts_required_minimal_package(tmp_path):
    create_minimal_release(tmp_path)

    assert audit_release_manifest.audit_release(tmp_path) == []


def test_release_manifest_flags_missing_required_file(tmp_path):
    create_minimal_release(tmp_path)
    (tmp_path / "replication/analysis/meta_regression.R").unlink()

    findings = audit_release_manifest.audit_release(tmp_path)

    assert any("missing required file: replication/analysis/meta_regression.R" in finding for finding in findings)


def test_release_manifest_flags_claude_state(tmp_path):
    create_minimal_release(tmp_path)
    path = tmp_path / "replication/.claude/scheduled_tasks.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("local state\n")

    findings = audit_release_manifest.audit_release(tmp_path)

    assert any("replication/.claude/scheduled_tasks.lock" in finding for finding in findings)


def test_release_manifest_flags_latex_build_products(tmp_path):
    create_minimal_release(tmp_path)
    (tmp_path / "replication/paper/latex/main.aux").write_text("build product\n")

    findings = audit_release_manifest.audit_release(tmp_path)

    assert any("replication/paper/latex/main.aux" in finding for finding in findings)
