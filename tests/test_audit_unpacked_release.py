import sys
import zipfile
from pathlib import Path

sys.path.insert(0, "tools")

import audit_unpacked_release


def test_unpacked_release_audit_flags_missing_zip(tmp_path):
    findings = audit_unpacked_release.audit_unpacked_zip(tmp_path / "missing.zip")

    assert findings == [f"missing release zip: {tmp_path / 'missing.zip'}"]


def test_unpacked_release_audit_flags_missing_replication_dir(tmp_path):
    zip_path = tmp_path / "package.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(f"{audit_unpacked_release.RELEASE_STEM}/COMMIT.txt", "abc\n")

    findings = audit_unpacked_release.audit_unpacked_zip(zip_path)

    assert findings == [
        (
            "missing replication directory inside zip: "
            f"{audit_unpacked_release.RELEASE_STEM}/replication"
        )
    ]


def test_unpacked_release_audit_runs_expected_commands(monkeypatch, tmp_path):
    zip_path = tmp_path / "package.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(f"{audit_unpacked_release.RELEASE_STEM}/COMMIT.txt", "abc\n")
        archive.writestr(
            f"{audit_unpacked_release.RELEASE_STEM}/replication/README.md",
            "replication\n",
        )
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, cwd, text, capture_output, check):
        calls.append((command, cwd))
        return Result()

    monkeypatch.setattr(audit_unpacked_release.subprocess, "run", fake_run)

    assert audit_unpacked_release.audit_unpacked_zip(zip_path) == []
    assert [command for command, _cwd in calls] == audit_unpacked_release.UNPACKED_COMMANDS
    assert all(cwd.name == "replication" for _command, cwd in calls)


def test_unpacked_release_audit_reports_command_failure(monkeypatch, tmp_path):
    zip_path = tmp_path / "package.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(f"{audit_unpacked_release.RELEASE_STEM}/COMMIT.txt", "abc\n")
        archive.writestr(
            f"{audit_unpacked_release.RELEASE_STEM}/replication/README.md",
            "replication\n",
        )

    class Result:
        returncode = 1
        stdout = ""
        stderr = "failed"

    monkeypatch.setattr(
        audit_unpacked_release.subprocess,
        "run",
        lambda *args, **kwargs: Result(),
    )

    findings = audit_unpacked_release.audit_unpacked_zip(zip_path)

    assert "failed inside unpacked release: failed" in findings[0]
