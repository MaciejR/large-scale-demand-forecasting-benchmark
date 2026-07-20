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


def test_token_audit_flags_missing_token_without_revealing_secret_names_only():
    findings = audit_zenodo_upload_readiness.audit_token(True, {})

    assert findings == [
        "missing Zenodo API token environment variable (ZENODO_ACCESS_TOKEN or ZENODO_TOKEN)"
    ]
