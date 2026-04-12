"""
Generate PRISMA 2020 flow diagram for the systematic review.

Produces: analysis/figures/prisma_flow.pdf + prisma_flow.png

Based on: Page MJ, et al. The PRISMA 2020 statement: an updated guideline
for reporting systematic reviews. BMJ 2021;372:n71.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── PRISMA Flow Numbers ──────────────────────────────────────────────────────
# Identification
N_DB_RECORDS = 250          # Records identified through database searching
N_QUERIES = 30              # Number of search queries executed
N_DATABASES = 5             # Databases searched
N_OTHER_SOURCES = 15        # Additional records from GIFT-Eval leaderboard, citation chasing, etc.
N_TOTAL_IDENTIFIED = N_DB_RECORDS + N_OTHER_SOURCES  # 265

# Screening
N_AFTER_DEDUP = 130         # After removing duplicates
N_DUPLICATES = N_TOTAL_IDENTIFIED - N_AFTER_DEDUP    # 135

N_SCREENED = N_AFTER_DEDUP  # Title/abstract screened
N_EXCLUDED_SCREENING = 81   # Excluded at screening (not demand/retail, no quant results)

# Eligibility
N_FULLTEXT_ASSESSED = N_SCREENED - N_EXCLUDED_SCREENING  # 49
N_EXCLUDED_FULLTEXT = 6     # 3 energy-only + 3 SCREEN still pending → exclude for now

# Inclusion
N_INCLUDED_QUALITATIVE = 43  # Studies in qualitative synthesis
N_INCLUDED_QUANTITATIVE = 35 # Studies with extractable metrics for meta-analysis

# Category breakdown
N_CAT_A = 16  # Foundation model papers
N_CAT_B = 8   # Benchmark papers
N_CAT_C = 12  # Retail-specific
N_CAT_D = 5   # DL baselines
N_CAT_E = 5   # Surveys (excluded from quantitative but in qualitative)
N_CAT_F = 4   # Cost/efficiency

# Exclusion reasons at full-text stage
EXCL_REASONS = [
    "Energy/electricity only (n=3)",
    "Pending full-text review (n=3)",
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
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # Title
    ax.text(5, 11.7, "PRISMA 2020 Flow Diagram", ha="center", va="center",
            fontsize=14, fontweight="bold", family="sans-serif")
    ax.text(5, 11.4,
            "Systematic Review: Foundation Models for Retail Demand Forecasting",
            ha="center", va="center", fontsize=9, fontstyle="italic",
            family="sans-serif", color="#555555")

    # ── Phase labels (left side) ─────────────────────────────────────────────
    phase_x = 0.6
    phases = [
        (10.5, "IDENTIFICATION"),
        (8.3, "SCREENING"),
        (6.2, "ELIGIBILITY"),
        (3.8, "INCLUDED"),
    ]
    for py, label in phases:
        ax.text(phase_x, py, label, ha="center", va="center", fontsize=8,
                fontweight="bold", rotation=90, color="#1976D2",
                family="sans-serif")

    # ── IDENTIFICATION ───────────────────────────────────────────────────────
    bw, bh = 3.2, 0.7  # box width, height

    draw_box(ax, 3.5, 10.5, bw, bh,
             f"Records identified through\ndatabase searching\n(n = {N_DB_RECORDS})",
             color="#E3F2FD", border="#1976D2", bold_first_line=True)

    draw_box(ax, 7.2, 10.5, bw, bh,
             f"Additional records from\nother sources\n(n = {N_OTHER_SOURCES})",
             color="#E3F2FD", border="#1976D2", bold_first_line=True)

    # Subtitle: databases
    ax.text(3.5, 9.85,
            f"{N_DATABASES} databases, {N_QUERIES}+ queries\n"
            "(Semantic Scholar, Google Scholar,\narXiv, Scopus, Web of Science)",
            ha="center", va="center", fontsize=7, color="#777777",
            family="sans-serif")

    ax.text(7.2, 9.95,
            "GIFT-Eval leaderboard,\ncitation chasing, grey literature",
            ha="center", va="center", fontsize=7, color="#777777",
            family="sans-serif")

    # ── Arrows: identification → screening ───────────────────────────────────
    draw_arrow(ax, 3.5, 10.1, 3.5, 9.2)
    draw_arrow(ax, 7.2, 10.1, 5.3, 9.2)

    # ── SCREENING ────────────────────────────────────────────────────────────
    draw_box(ax, 4.2, 8.8, 3.5, 0.65,
             f"Records after duplicates removed\n(n = {N_AFTER_DEDUP})",
             color="#E8F5E9", border="#388E3C", bold_first_line=True)

    draw_arrow(ax, 4.2, 8.47, 4.2, 7.95)

    draw_box(ax, 4.2, 7.6, 3.5, 0.65,
             f"Titles/abstracts screened\n(n = {N_SCREENED})",
             color="#E8F5E9", border="#388E3C", bold_first_line=True)

    # Exclusion box (right)
    draw_box(ax, 8.2, 7.6, 2.5, 0.65,
             f"Records excluded\n(n = {N_EXCLUDED_SCREENING})",
             color="#FFEBEE", border="#D32F2F")

    draw_side_arrow(ax, 5.95, 7.6, 6.95, 7.6, color="#D32F2F")

    ax.text(8.2, 7.1,
            "Not demand/retail forecasting,\nno quantitative results,\nduplicate/superseded",
            ha="center", va="center", fontsize=7, color="#999999",
            family="sans-serif")

    # Duplicates removed (right of dedup box)
    draw_box(ax, 8.2, 8.8, 2.5, 0.55,
             f"Duplicates removed\n(n = {N_DUPLICATES})",
             color="#FFF3E0", border="#F57C00")
    draw_side_arrow(ax, 5.95, 8.8, 6.95, 8.8, color="#F57C00")

    # ── ELIGIBILITY ──────────────────────────────────────────────────────────
    draw_arrow(ax, 4.2, 7.27, 4.2, 6.75)

    draw_box(ax, 4.2, 6.4, 3.5, 0.65,
             f"Full-text articles assessed\nfor eligibility\n(n = {N_FULLTEXT_ASSESSED})",
             color="#FFF8E1", border="#F9A825", bold_first_line=True)

    # Exclusion box (right)
    draw_box(ax, 8.2, 6.4, 2.5, 0.65,
             f"Full-text articles excluded\n(n = {N_EXCLUDED_FULLTEXT})",
             color="#FFEBEE", border="#D32F2F")

    draw_side_arrow(ax, 5.95, 6.4, 6.95, 6.4, color="#D32F2F")

    reasons_text = "\n".join(EXCL_REASONS)
    ax.text(8.2, 5.85, reasons_text,
            ha="center", va="center", fontsize=7, color="#999999",
            family="sans-serif")

    # ── INCLUDED ─────────────────────────────────────────────────────────────
    draw_arrow(ax, 4.2, 6.07, 4.2, 5.45)

    draw_box(ax, 4.2, 5.1, 3.5, 0.65,
             f"Studies included in\nqualitative synthesis\n(n = {N_INCLUDED_QUALITATIVE})",
             color="#E8EAF6", border="#3F51B5", bold_first_line=True)

    draw_arrow(ax, 4.2, 4.77, 4.2, 4.15)

    draw_box(ax, 4.2, 3.8, 3.5, 0.65,
             f"Studies included in\nquantitative meta-analysis\n(n = {N_INCLUDED_QUANTITATIVE})",
             color="#E8EAF6", border="#3F51B5", bold_first_line=True)

    # Excluded from quantitative (right)
    n_qual_only = N_INCLUDED_QUALITATIVE - N_INCLUDED_QUANTITATIVE
    draw_box(ax, 8.2, 5.1, 2.5, 0.55,
             f"Qualitative only\n(n = {n_qual_only})",
             color="#F3E5F5", border="#7B1FA2")
    draw_side_arrow(ax, 5.95, 5.1, 6.95, 5.1, color="#7B1FA2")

    ax.text(8.2, 4.6,
            "Surveys without own data (n=5),\nmethod papers without\nretail benchmarks (n=3)",
            ha="center", va="center", fontsize=7, color="#999999",
            family="sans-serif")

    # ── Category breakdown ───────────────────────────────────────────────────
    draw_arrow(ax, 4.2, 3.47, 4.2, 2.9)

    # Category breakdown box
    cat_text = (
        f"Category Breakdown\n"
        f"A: Foundation model papers (n={N_CAT_A})\n"
        f"B: Benchmark papers (n={N_CAT_B})\n"
        f"C: Retail-specific studies (n={N_CAT_C})\n"
        f"D: Deep learning baselines (n={N_CAT_D})\n"
        f"E: Surveys/meta-studies (n={N_CAT_E})\n"
        f"F: Cost/efficiency analysis (n={N_CAT_F})"
    )
    draw_box(ax, 4.2, 1.9, 5.0, 1.6, cat_text,
             color="#ECEFF1", border="#546E7A", fontsize=8,
             bold_first_line=True)

    # ── Extraction stats (bottom right) ──────────────────────────────────────
    ax.text(8.5, 1.0,
            "Extraction: 90 rows\nacross 15+ papers\nin extraction_schema.csv",
            ha="center", va="center", fontsize=7,
            family="sans-serif", color="#666666",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#F5F5F5",
                      edgecolor="#BDBDBD"))

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
