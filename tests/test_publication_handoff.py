from pathlib import Path


def test_publication_handoff_contains_finalization_commands():
    text = Path("docs/PUBLICATION_HANDOFF_V1.12.md").read_text()

    required = [
        "tools/build_v112_release.sh",
        "python3 tools/audit_publication_readiness.py",
        "python3 tools/audit_publication_readiness.py --require-public",
        "python3 tools/audit_publication_log_v112.py",
        "gh repo edit MaciejR/large-scale-demand-forecasting-benchmark --visibility public",
        "release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip",
        "shasum -a 256 release/zenodo-v1.12-timesfm-fev-bench-wape-covariance-repair.zip",
    ]

    for phrase in required:
        assert phrase in text


def test_readme_points_to_publication_handoff():
    readme = Path("README.md").read_text()

    assert "docs/PUBLICATION_HANDOFF_V1.12.md" in readme
