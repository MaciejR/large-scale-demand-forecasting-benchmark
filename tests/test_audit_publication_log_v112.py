import sys

sys.path.insert(0, "tools")

import audit_publication_log_v112


def valid_log():
    return "\n".join(
        [
            audit_publication_log_v112.GITHUB_RELEASE_URL,
            audit_publication_log_v112.ASSET_NAME,
            "Target commit: TODO",
            "Asset SHA-256: TODO",
            "Production deposition ID: TODO",
            "Production record URL: TODO",
            "Production DOI: TODO",
            "DOI metadata update commit: TODO",
            "Final package SHA-256 after DOI update: TODO",
            "Final GitHub release target after DOI update: TODO",
        ]
    )


def test_publication_log_accepts_required_template_fields():
    assert audit_publication_log_v112.audit_log_text(valid_log()) == []


def test_publication_log_flags_missing_field():
    findings = audit_publication_log_v112.audit_log_text(
        valid_log().replace("Asset SHA-256: TODO", "")
    )

    assert findings == ["publication log missing field: Asset SHA-256:"]


def test_complete_publication_log_flags_todo_and_missing_doi():
    findings = audit_publication_log_v112.audit_complete_log_text("Production DOI: TODO")

    assert "publication log still contains TODO placeholders" in findings
    assert "publication log does not contain a Zenodo DOI" in findings
    assert "publication log does not contain a production DOI URL" in findings
    assert "publication log does not contain a production record URL" in findings


def test_complete_publication_log_accepts_doi_record_and_no_todo():
    text = (
        "Production DOI: 10.5281/zenodo.99999999\n"
        "Production DOI URL: https://doi.org/10.5281/zenodo.99999999\n"
        "Production record URL: https://zenodo.org/records/99999999"
    )

    assert audit_publication_log_v112.audit_complete_log_text(text) == []
