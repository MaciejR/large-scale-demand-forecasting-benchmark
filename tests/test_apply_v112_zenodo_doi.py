import sys

sys.path.insert(0, "tools")

import apply_v112_zenodo_doi


def test_validate_doi_accepts_v112_style_doi():
    assert apply_v112_zenodo_doi.validate_doi("10.5281/zenodo.99999999") == (
        "10.5281/zenodo.99999999"
    )


def test_validate_doi_rejects_historical_v1_doi():
    try:
        apply_v112_zenodo_doi.validate_doi(apply_v112_zenodo_doi.HISTORICAL_DOI)
    except ValueError as exc:
        assert "historical v1.0 DOI" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_update_citation_adds_doi_and_doi_url():
    original = (
        'message: "If you use the current repair package, cite this repository version or '
        'the corresponding Zenodo archive when minted."\n'
        'url: "https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.12"\n'
    )

    updated = apply_v112_zenodo_doi.update_citation(original, "10.5281/zenodo.99999999")

    assert 'doi: "10.5281/zenodo.99999999"' in updated
    assert 'url: "https://doi.org/10.5281/zenodo.99999999"' in updated
    assert "when minted" not in updated


def test_update_release_notes_is_idempotent():
    original = (
        "# Release Notes: v1.12 TimesFM fev-bench WAPE Covariance Repair\n\n"
        "Release commit: recorded in the release package `COMMIT.txt`.\n"
    )

    once = apply_v112_zenodo_doi.update_release_notes(original, "10.5281/zenodo.99999999")
    twice = apply_v112_zenodo_doi.update_release_notes(once, "10.5281/zenodo.99999999")

    assert once == twice
    assert once.count("https://doi.org/10.5281/zenodo.99999999") == 1


def test_update_main_tex_replaces_current_data_availability_block():
    original = (
        "the release package corresponding to this manuscript is prepared as a\n"
        "versioned Zenodo-ready archive under \\path{release/} rather than overwriting the\n"
        "historical snapshot, and is published as GitHub release v1.12 at\n"
        "\\url{https://github.com/MaciejR/large-scale-demand-forecasting-benchmark/releases/tag/v1.12}."
    )

    updated = apply_v112_zenodo_doi.update_main_tex(original, "10.5281/zenodo.99999999")

    assert "Zenodo-ready" not in updated
    assert "\\url{https://doi.org/10.5281/zenodo.99999999}" in updated
    assert "GitHub release v1.12" in updated
