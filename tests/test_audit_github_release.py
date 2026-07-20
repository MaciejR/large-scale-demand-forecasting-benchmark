import sys

sys.path.insert(0, "tools")

import audit_github_release


def payload(asset_overrides=None, release_overrides=None):
    asset = {
        "name": audit_github_release.ASSET_NAME,
        "size": 3,
        "digest": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "url": (
            "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/"
            "releases/download/v1.12/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip"
        ),
        "state": "uploaded",
    }
    if asset_overrides:
        asset.update(asset_overrides)

    release = {
        "tagName": "v1.12",
        "url": "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.12",
        "targetCommitish": "abc123",
        "isDraft": False,
        "isPrerelease": False,
        "assets": [asset],
    }
    if release_overrides:
        release.update(release_overrides)
    return release


def test_github_release_payload_accepts_matching_asset(tmp_path):
    zip_path = tmp_path / audit_github_release.ASSET_NAME
    zip_path.write_bytes(b"abc")

    assert audit_github_release.audit_payload(payload(), "abc123", zip_path) == []


def test_github_release_payload_flags_target_mismatch(tmp_path):
    zip_path = tmp_path / audit_github_release.ASSET_NAME
    zip_path.write_bytes(b"abc")

    findings = audit_github_release.audit_payload(payload(), "def456", zip_path)

    assert any("release target is abc123, expected def456" in finding for finding in findings)


def test_github_release_payload_flags_digest_mismatch(tmp_path):
    zip_path = tmp_path / audit_github_release.ASSET_NAME
    zip_path.write_bytes(b"abc")

    findings = audit_github_release.audit_payload(
        payload(asset_overrides={"digest": "sha256:not-the-local-file"}),
        "abc123",
        zip_path,
    )

    assert any("asset digest is sha256:not-the-local-file" in finding for finding in findings)


def test_github_release_payload_flags_missing_asset(tmp_path):
    zip_path = tmp_path / audit_github_release.ASSET_NAME
    zip_path.write_bytes(b"abc")

    findings = audit_github_release.audit_payload(
        payload(release_overrides={"assets": []}),
        "abc123",
        zip_path,
    )

    assert findings == [f"missing release asset: {audit_github_release.ASSET_NAME}"]
