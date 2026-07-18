"""
Generate PRISMA 2020 flow diagram for the systematic review.

Produces: analysis/figures/prisma_flow.pdf + prisma_flow.png

Based on: Page MJ, et al. The PRISMA 2020 statement: an updated guideline
for reporting systematic reviews. BMJ 2021;372:n71.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# PRISMA flow numbers aligned with the repaired manuscript.
# Identification
N_DB_RECORDS = 150          # Records identified through database/web searching
N_QUERIES = 25              # Auditable query families retained in Appendix B
N_DATABASES = 3             # Auditable exports/checks retained: Google Scholar/web, Semantic Scholar, arXiv
N_OTHER_SOURCES = 0         # Database/web searching accounts for all 150 records
N_TOTAL_IDENTIFIED = N_DB_RECORDS + N_OTHER_SOURCES

# Screening
N_DUPLICATES = 30           # Cross-source overlap among retained auditable records
N_AFTER_DEDUP = N_TOTAL_IDENTIFIED - N_DUPLICATES    # ~120

N_SCREENED = N_AFTER_DEDUP  # Title/abstract screened
N_EXCLUDED_SCREENING = 50   # Non-retail, no quantitative results, financial only

# Eligibility
N_FULLTEXT_ASSESSED = N_SCREENED - N_EXCLUDED_SCREENING  # ~70
N_EXCLUDED_FULLTEXT = 38    # No retail dataset, no FM evaluation, duplicate results

# Inclusion
N_INCLUDED = 32             # External Source A studies only
N_INCLUDED_EXTERNAL = 32    # External papers
N_OWN_EXPERIMENTS = 7       # Own experiment blocks (Source B)
N_EXTRACTION_ROWS_LABEL = "802"   # Frozen extraction_schema.csv rows after per-task re-extraction

N_CAT_A = 17  # Foundation model papers
N_CAT_B = 4   # Benchmark papers
N_CAT_C = 8   # Retail-specific ML/DL
N_CAT_D = 3   # Cross-domain papers

# Exclusion reasons at full-text stage
EXCL_REASONS = [
    "No retail dataset (n=14)",
    "No FM evaluation (n=12)",
    "Duplicate/non-comparable results (n=12)",
]


def draw_box(ax, x, y, w, h, text, color="#E8F4FD", border="#2196F3", fontsize=9,
             bold_first_line=False):
    """Draw a rounded rectangle with centered text."""
    box = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02",
        facecolor=color, edgecolor=border, linewidth=1.5
    )
    ax.add_patch(box)

    lines = text.split("\n")
    if bold_first_line and len(lines) > 1:
        # First line bold, rest normal
        line_height = fontsize * 1.8 / 72  # rough pt-to-inches
        total_height = len(lines) * line_height
        top_y = y + total_height / 2 - line_height / 2
        for i, line in enumerate(lines):
            weight = "bold" if i == 0 else "normal"
            fs = fontsize if i == 0 else fontsize - 0.5
            ax.text(x, top_y - i * line_height, line,
                    ha="center", va="center", fontsize=fs,
                    fontweight=weight, family="sans-serif")
    else:
        ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
                family="sans-serif")


def draw_arrow(ax, x1, y1, x2, y2, color="#666666"):
    """Draw an arrow between two points."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2))


def draw_side_arrow(ax, x1, y1, x2, y2, color="#999999"):
    """Draw a right-pointing arrow (for exclusions)."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0,
                                linestyle="--"))


def main():
    fig, ax = plt.subplots(1, 1, figsize=(10, 11))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis("off")

    # Title
    ax.text(5, 10.7, "PRISMA-Informed Flow Diagram", ha="center", va="center",
            fontsize=14, fontweight="bold", family="sans-serif")
    ax.text(5, 10.4,
            "Systematic Review: Foundation Models for Retail Demand Forecasting",
            ha="center", va="center", fontsize=9, fontstyle="italic",
            family="sans-serif", color="#555555")

    # ── Phase labels (left side) ─────────────────────────────────────────────
    phase_x = 0.6
    phases = [
        (9.5, "IDENTIFICATION"),
        (7.5, "SCREENING"),
        (5.7, "ELIGIBILITY"),
        (3.4, "INCLUDED"),
    ]
    for py, label in phases:
        ax.text(phase_x, py, label, ha="center", va="center", fontsize=8,
                fontweight="bold", rotation=90, color="#1976D2",
                family="sans-serif")

    # ── IDENTIFICATION ───────────────────────────────────────────────────────
    bw, bh = 3.2, 0.7

    draw_box(ax, 3.5, 9.5, bw, bh,
             f"Records identified through\ndatabase/web searching\n(n = {N_DB_RECORDS})",
             color="#E3F2FD", border="#1976D2", bold_first_line=True)

    draw_box(ax, 7.2, 9.5, bw, bh,
             f"Additional records from\nother sources\n(n = {N_OTHER_SOURCES})",
             color="#E3F2FD", border="#1976D2", bold_first_line=True)

    ax.text(3.5, 8.95,
            f"{N_DATABASES} auditable sources, {N_QUERIES} query families",
            ha="center", va="center", fontsize=8, color="#777777",
            family="sans-serif")

    # ── Arrows: identification → screening ───────────────────────────────────
    draw_arrow(ax, 3.5, 9.1, 3.5, 8.35)
    draw_arrow(ax, 7.2, 9.1, 5.3, 8.35)

    # ── SCREENING ────────────────────────────────────────────────────────────
    draw_box(ax, 4.2, 8.0, 3.5, 0.65,
             f"Records after duplicates removed\n(n = {N_AFTER_DEDUP})",
             color="#E8F5E9", border="#388E3C", bold_first_line=True)

    draw_arrow(ax, 4.2, 7.67, 4.2, 7.15)

    draw_box(ax, 4.2, 6.8, 3.5, 0.65,
             f"Titles/abstracts screened\n(n = {N_SCREENED})",
             color="#E8F5E9", border="#388E3C", bold_first_line=True)

    # Exclusion box (right)
    draw_box(ax, 8.2, 6.8, 2.5, 0.65,
             f"Records excluded\n(n = {N_EXCLUDED_SCREENING})",
             color="#FFEBEE", border="#D32F2F")

    draw_side_arrow(ax, 5.95, 6.8, 6.95, 6.8, color="#D32F2F")

    draw_box(ax, 8.2, 8.0, 2.5, 0.55,
             f"Duplicates removed\n(n = {N_DUPLICATES})",
             color="#FFF3E0", border="#F57C00")
    draw_side_arrow(ax, 5.95, 8.0, 6.95, 8.0, color="#F57C00")

    # ── ELIGIBILITY ──────────────────────────────────────────────────────────
    draw_arrow(ax, 4.2, 6.47, 4.2, 5.95)

    draw_box(ax, 4.2, 5.6, 3.5, 0.65,
             f"Full-text articles assessed\nfor eligibility\n(n = {N_FULLTEXT_ASSESSED})",
             color="#FFF8E1", border="#F9A825", bold_first_line=True)

    # Exclusion box (right)
    draw_box(ax, 8.2, 5.6, 2.5, 0.65,
             f"Full-text articles excluded\n(n = {N_EXCLUDED_FULLTEXT})",
             color="#FFEBEE", border="#D32F2F")

    draw_side_arrow(ax, 5.95, 5.6, 6.95, 5.6, color="#D32F2F")

    reasons_text = "\n".join(EXCL_REASONS)
    ax.text(8.2, 5.05, reasons_text,
            ha="center", va="center", fontsize=8, color="#777777",
            family="sans-serif")

    # ── INCLUDED ─────────────────────────────────────────────────────────────
    draw_arrow(ax, 4.2, 5.27, 4.2, 4.65)

    draw_box(ax, 4.2, 4.3, 3.5, 0.65,
             f"Source A studies included\n(n = {N_INCLUDED_EXTERNAL} external papers)",
             color="#E8EAF6", border="#3F51B5", bold_first_line=True)

    draw_arrow(ax, 4.2, 3.97, 4.2, 3.35)

    draw_box(ax, 4.2, 3.0, 3.5, 0.65,
             f"Extraction rows after per-task\nbenchmark re-extraction\n(n = {N_EXTRACTION_ROWS_LABEL})",
             color="#E8EAF6", border="#3F51B5", bold_first_line=True)

    draw_box(ax, 8.2, 4.3, 2.5, 0.55,
             f"Source B: own experiments\n(not PRISMA studies; local sweep n=72)",
             color="#F3E5F5", border="#7B1FA2")
    draw_side_arrow(ax, 5.95, 4.3, 6.95, 4.3, color="#7B1FA2")

    # ── Category breakdown ───────────────────────────────────────────────────
    draw_arrow(ax, 4.2, 2.67, 4.2, 2.1)

    # Category breakdown box
    cat_text = (
        f"Category Breakdown\n"
        f"A: Foundation model papers (n={N_CAT_A})\n"
        f"B: Benchmark papers (n={N_CAT_B})\n"
        f"C: Retail ML/DL papers (n={N_CAT_C})\n"
        f"D: Cross-domain papers (n={N_CAT_D})\n"
        "Source B: gap-filling experiments reported separately"
    )
    draw_box(ax, 4.2, 1.2, 5.0, 1.4, cat_text,
             color="#ECEFF1", border="#546E7A", fontsize=8,
             bold_first_line=True)

    # ── Save ─────────────────────────────────────────────────────────────────
    import os
    os.makedirs("analysis/figures", exist_ok=True)

    plt.tight_layout()
    fig.savefig("analysis/figures/prisma_flow.pdf", bbox_inches="tight", dpi=300)
    fig.savefig("analysis/figures/prisma_flow.png", bbox_inches="tight", dpi=300)
    print("Saved: analysis/figures/prisma_flow.pdf")
    print("Saved: analysis/figures/prisma_flow.png")
    plt.close()


if __name__ == "__main__":
    main()
