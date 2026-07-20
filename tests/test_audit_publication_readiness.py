import sys
from pathlib import Path

sys.path.insert(0, "tools")

import audit_publication_readiness


def test_publication_visibility_allows_private_without_require_public(monkeypatch):
    monkeypatch.setattr(
        audit_publication_readiness,
        "github_visibility",
        lambda repo_root: ("PRIVATE", None),
    )

    assert audit_publication_readiness.audit_github_visibility(Path("."), require_public=False) == []


def test_publication_visibility_flags_private_when_public_required(monkeypatch):
    monkeypatch.setattr(
        audit_publication_readiness,
        "github_visibility",
        lambda repo_root: ("PRIVATE", None),
    )

    findings = audit_publication_readiness.audit_github_visibility(Path("."), require_public=True)

    assert findings == ["GitHub repository visibility is PRIVATE, expected PUBLIC"]


def test_publication_visibility_accepts_public_when_required(monkeypatch):
    monkeypatch.setattr(
        audit_publication_readiness,
        "github_visibility",
        lambda repo_root: ("PUBLIC", None),
    )

    assert audit_publication_readiness.audit_github_visibility(Path("."), require_public=True) == []


def test_publication_visibility_reports_gh_error(monkeypatch):
    monkeypatch.setattr(
        audit_publication_readiness,
        "github_visibility",
        lambda repo_root: (None, "gh unavailable"),
    )

    assert audit_publication_readiness.audit_github_visibility(Path("."), require_public=False) == [
        "gh unavailable"
    ]


def test_release_audit_includes_publication_log_gate(monkeypatch):
    commands = []

    monkeypatch.setattr(audit_publication_readiness, "run", lambda cmd, cwd: "abc123")

    def fake_try_run(cmd, cwd):
        commands.append(cmd)
        return 0, "", ""

    monkeypatch.setattr(audit_publication_readiness, "try_run", fake_try_run)
    monkeypatch.setattr(Path, "is_dir", lambda self: True)
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: "abc123")

    assert audit_publication_readiness.audit_release(Path(".")) == []
    assert ["python3", "tools/audit_publication_log_v112.py"] in commands


def test_require_public_runs_download_verified_github_release_audit(monkeypatch):
    commands = []

    monkeypatch.setattr(audit_publication_readiness, "audit_git", lambda repo_root: [])
    monkeypatch.setattr(audit_publication_readiness, "audit_release", lambda repo_root: [])
    monkeypatch.setattr(
        audit_publication_readiness,
        "audit_github_visibility",
        lambda repo_root, require_public: [],
    )

    def fake_try_run(cmd, cwd):
        commands.append(cmd)
        return 0, "", ""

    monkeypatch.setattr(audit_publication_readiness, "try_run", fake_try_run)

    assert audit_publication_readiness.audit(Path("."), require_public=True) == []
    assert [
        "python3",
        "tools/audit_github_release.py",
        "--verify-download",
    ] in commands
