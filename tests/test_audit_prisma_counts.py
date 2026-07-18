import sys

sys.path.insert(0, "tools")

import audit_prisma_counts


def test_prisma_arithmetic_invariants_hold():
    expected = audit_prisma_counts.EXPECTED

    assert expected["records_identified"] - expected["duplicates_removed"] == expected["after_dedup"]
    assert expected["screened"] - expected["excluded_screening"] == expected["fulltext_assessed"]
    assert expected["fulltext_assessed"] - expected["excluded_fulltext"] == expected["source_a_included"]
    assert (
        expected["category_a"]
        + expected["category_b"]
        + expected["category_c"]
        + expected["category_d"]
        == expected["source_a_included"]
    )


def test_current_prisma_counts_are_consistent_across_artifacts():
    assert audit_prisma_counts.main() == 0
