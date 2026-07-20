import copy
import sys

sys.path.insert(0, "tools")

import audit_zenodo_metadata


def valid_metadata():
    return {
        "title": "When Do Foundation Models Pay Off for Retail Demand Forecasting? v1.12 TimesFM fev-bench WAPE Covariance Repair",
        "upload_type": "publication",
        "publication_type": "technicalnote",
        "publication_date": "2026-07-20",
        "creators": [{"name": "Rubczynski, Maciej"}],
        "description": "A package.",
        "keywords": [
            "demand forecasting",
            "foundation models",
            "TimesFM",
            "reproducibility",
        ],
        "version": audit_zenodo_metadata.VERSION,
        "language": "eng",
        "access_right": "open",
        "license": "cc-by-4.0",
        "related_identifiers": [
            {
                "identifier": audit_zenodo_metadata.GITHUB_REPO_URL,
                "relation": "isSupplementTo",
            },
            {
                "identifier": audit_zenodo_metadata.GITHUB_RELEASE_URL,
                "relation": "isIdenticalTo",
            },
            {
                "identifier": audit_zenodo_metadata.HISTORICAL_DOI,
                "relation": "isNewVersionOf",
            },
        ],
        "notes": (
            f"GitHub release asset: {audit_zenodo_metadata.ASSET_NAME}; "
            "source commit recorded in COMMIT.txt inside the archive; "
            "file hashes recorded in CHECKSUMS.txt inside the archive."
        ),
    }


def test_zenodo_metadata_accepts_valid_minimal_metadata():
    assert audit_zenodo_metadata.audit_metadata(valid_metadata()) == []


def test_zenodo_metadata_flags_wrong_version():
    metadata = valid_metadata()
    metadata["version"] = "v1.0"

    findings = audit_zenodo_metadata.audit_metadata(metadata)

    assert any("version='v1.0'" in finding for finding in findings)


def test_zenodo_metadata_flags_missing_github_release_relation():
    metadata = copy.deepcopy(valid_metadata())
    metadata["related_identifiers"] = metadata["related_identifiers"][:1]

    findings = audit_zenodo_metadata.audit_metadata(metadata)

    assert any(audit_zenodo_metadata.GITHUB_RELEASE_URL in finding for finding in findings)


def test_zenodo_metadata_flags_missing_checksums_note():
    metadata = valid_metadata()
    metadata["notes"] = f"GitHub release asset: {audit_zenodo_metadata.ASSET_NAME}; COMMIT.txt"

    findings = audit_zenodo_metadata.audit_metadata(metadata)

    assert findings == ["notes missing 'CHECKSUMS.txt'"]


def test_root_zenodo_metadata_matches_draft():
    assert audit_zenodo_metadata.load_metadata(
        audit_zenodo_metadata.ROOT_METADATA_PATH
    ) == audit_zenodo_metadata.load_metadata(audit_zenodo_metadata.METADATA_PATH)
