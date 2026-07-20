from pathlib import Path


SCRIPT = Path("tools/publish_v112_zenodo.sh")


def test_publish_wrapper_runs_common_publication_audits():
    text = SCRIPT.read_text()

    for command in [
        "python3 tools/audit_publication_readiness.py --require-public",
        "python3 tools/audit_github_release.py",
        "python3 tools/audit_publication_log_v112.py",
    ]:
        assert command in text


def test_publish_wrapper_requires_tokens_for_mutating_actions():
    text = SCRIPT.read_text()

    assert "python3 tools/audit_zenodo_upload_readiness.py --require-token" in text
    assert (
        "python3 tools/audit_zenodo_upload_readiness.py --require-token --sandbox-token"
        in text
    )


def test_publish_wrapper_publish_requires_deposition_id():
    text = SCRIPT.read_text()

    assert 'echo "publish requires --deposition-id ID"' in text
    assert "--publish" in text
    assert '--deposition-id "$deposition_id"' in text
