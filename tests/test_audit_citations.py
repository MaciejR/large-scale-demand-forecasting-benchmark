import sys

sys.path.insert(0, "tools")

import audit_citations


def test_citation_regex_handles_optional_arguments_and_multiple_keys():
    text = r"""
    \citep[see][chap.~2]{alpha2024, beta2025}
    \citet{gamma2026}
    \citealp[p.~10]{delta2026}
    """

    keys = set()
    for match in audit_citations.CITE_RE.finditer(text):
        keys.update(key.strip() for key in match.group(1).split(",") if key.strip())

    assert keys == {"alpha2024", "beta2025", "gamma2026", "delta2026"}


def test_current_manuscript_citations_resolve():
    assert audit_citations.main() == 0
