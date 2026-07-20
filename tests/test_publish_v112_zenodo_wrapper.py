from pathlib import Path


SCRIPT = Path("tools/publish_v112_zenodo.sh")


def test_publish_wrapper_runs_common_publication_audits():
    text = SCRIPT.read_text()

    for command in [
        "python3 tools/audit_publication_readiness.py --require-public",
        "python3 tools/audit_publication_log_v112.py",
    ]:
        assert command in text


def test_publish_wrapper_avoids_duplicate_release_asset_download():
    text = SCRIPT.read_text()

    assert "python3 tools/audit_github_release.py --verify-download" not in text


def test_publish_wrapper_requires_tokens_for_mutating_actions():
    text = SCRIPT.read_text()

    assert "python3 tools/audit_zenodo_upload_readiness.py --require-token" in text
    assert (
        "python3 tools/audit_zenodo_upload_readiness.py --require-token --sandbox-token"
        in text
    )


def test_publish_wrapper_imports_only_known_local_env_tokens():
    text = SCRIPT.read_text()

    assert "load_local_env_tokens" in text
    assert "ZENODO_ACCESS_TOKEN|ZENODO_TOKEN|ZENODO_SANDBOX_ACCESS_TOKEN|ZENODO_SANDBOX_TOKEN" in text
    assert 'source ".env"' not in text
    assert "source .env" not in text


def test_publish_wrapper_publish_requires_deposition_id():
    text = SCRIPT.read_text()

    assert 'echo "publish requires --deposition-id ID"' in text
    assert "--publish" in text
    assert '--deposition-id "$deposition_id"' in text


def test_publish_wrapper_does_not_mutate_publication_log():
    text = SCRIPT.read_text()

    assert "tools/update_publication_log_v112.py" not in text
