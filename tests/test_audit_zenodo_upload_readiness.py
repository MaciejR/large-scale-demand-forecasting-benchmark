import sys

sys.path.insert(0, "tools")

import audit_zenodo_upload_readiness


def test_token_audit_is_optional():
    assert audit_zenodo_upload_readiness.audit_token(False, {}) == []


def test_token_audit_accepts_access_token():
    findings = audit_zenodo_upload_readiness.audit_token(
        True,
        {"ZENODO_ACCESS_TOKEN": "secret-value"},
    )

    assert findings == []


def test_token_audit_accepts_legacy_token_name():
    findings = audit_zenodo_upload_readiness.audit_token(
        True,
        {"ZENODO_TOKEN": "secret-value"},
    )

    assert findings == []


def test_token_audit_accepts_sandbox_token_names():
    findings = audit_zenodo_upload_readiness.audit_token(
        True,
        {"ZENODO_SANDBOX_ACCESS_TOKEN": "secret-value"},
        token_env_vars=audit_zenodo_upload_readiness.SANDBOX_TOKEN_ENV_VARS,
    )

    assert findings == []


def test_token_audit_flags_missing_token_without_revealing_secret_names_only():
    findings = audit_zenodo_upload_readiness.audit_token(True, {})

    assert findings == [
        "missing Zenodo API token environment variable (ZENODO_ACCESS_TOKEN or ZENODO_TOKEN)"
    ]


def test_token_audit_reports_sandbox_token_names_when_requested():
    findings = audit_zenodo_upload_readiness.audit_token(
        True,
        {},
        token_env_vars=audit_zenodo_upload_readiness.SANDBOX_TOKEN_ENV_VARS,
    )

    assert findings == [
        "missing Zenodo API token environment variable "
        "(ZENODO_SANDBOX_ACCESS_TOKEN or ZENODO_SANDBOX_TOKEN)"
    ]


def test_token_audit_rejects_placeholder_values():
    findings = audit_zenodo_upload_readiness.audit_token(
        True,
        {"ZENODO_ACCESS_TOKEN": "TODO"},
    )

    assert findings == [
        "Zenodo API token environment variable is a placeholder (ZENODO_ACCESS_TOKEN)"
    ]


def test_token_audit_accepts_valid_token_when_other_alias_is_placeholder():
    findings = audit_zenodo_upload_readiness.audit_token(
        True,
        {"ZENODO_ACCESS_TOKEN": "changeme", "ZENODO_TOKEN": "secret-value"},
    )

    assert findings == []


def test_local_env_tokens_are_loaded_without_overriding_environment(tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "ZENODO_ACCESS_TOKEN=local-production-token",
                "ZENODO_TOKEN=local-legacy-token",
                "OTHER_SECRET=must-not-load",
            ]
        ),
        encoding="utf-8",
    )

    environ = {"ZENODO_ACCESS_TOKEN": "process-token"}
    merged = audit_zenodo_upload_readiness.load_local_env_tokens(tmp_path, environ)

    assert merged["ZENODO_ACCESS_TOKEN"] == "process-token"
    assert merged["ZENODO_TOKEN"] == "local-legacy-token"
    assert "OTHER_SECRET" not in merged


def test_local_env_token_loader_handles_quotes_and_sandbox_names(tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                'ZENODO_SANDBOX_ACCESS_TOKEN="sandbox-access"',
                "ZENODO_SANDBOX_TOKEN='sandbox-legacy'",
            ]
        ),
        encoding="utf-8",
    )

    merged = audit_zenodo_upload_readiness.load_local_env_tokens(tmp_path, {})

    assert merged["ZENODO_SANDBOX_ACCESS_TOKEN"] == "sandbox-access"
    assert merged["ZENODO_SANDBOX_TOKEN"] == "sandbox-legacy"
