# Publication Strategy

Last updated: 2026-07-13

This document turns the v1.0 Zenodo technical report into a practical
publication plan. The current record is already public and citable:
<https://doi.org/10.5281/zenodo.21338004>.

## Recommended Path

Recommended sequence:

1. Prepare an arXiv-oriented v1.1 manuscript.
2. Ask one forecasting/time-series researcher for external review or
   collaboration before journal submission.
3. Submit the revised article to a peer-reviewed forecasting or applied-ML
   journal.

Rationale: Zenodo already provides the DOI and archival record. The next useful
step is visibility and feedback, not another archival upload. arXiv is the best
bridge for discovery if the manuscript is tightened and the source package is
made arXiv-compatible. A journal submission should follow only after the main
text is shorter and the methodological framing has been reviewed by someone in
forecasting or time-series evaluation.

## Stage 1: arXiv v1.1

Goal: produce a readable preprint version that points to the Zenodo DOI and the
GitHub release.

Recommended arXiv positioning:

- Primary category: `cs.LG` if framed as benchmark/meta-analysis evidence about
  machine-learning foundation models.
- Possible cross-list: `stat.ML` if the meta-regression and statistical
  evaluation framing becomes central.
- Comment field: `Technical report v1.1; 25--35 pages main text plus appendices;
  code and replication materials archived at Zenodo DOI 10.5281/zenodo.21338004`.

Required preparation:

- Reduce the main narrative to roughly 25--35 pages before appendices.
- Move long extraction tables, detailed threat taxonomy, and secondary
  sensitivity details into appendices or Zenodo/GitHub references.
- Keep the abstract more cautious than a journal abstract: "benchmark-level
  evidence" rather than universal superiority.
- Add an explicit "Relation to the Zenodo technical report" note.
- Build an arXiv source package from LaTeX source, not only the PDF.
- Check whether the account needs arXiv endorsement for `cs.LG` or `stat.ML`.

Current arXiv facts checked on 2026-07-13:

- arXiv submission guidelines say PDF generated from TeX/LaTeX source is not
  accepted as the source format; submit TeX/LaTeX source instead.
- arXiv may require endorsement before first submission or first submission to a
  new category.
- Submissions are moderated for topical fit and scientific relevance; moderation
  is not peer review.

Official references:

- arXiv submission guidelines:
  <https://info.arxiv.org/help/submit/index.html>
- arXiv TeX/LaTeX submission help:
  <https://info.arxiv.org/help/submit_tex.html>
- arXiv endorsement:
  <https://info.arxiv.org/help/endorsement.html>

## Stage 2: External Reviewer or Collaborator

Goal: get one domain expert to pressure-test the claims before journal review.

Best-fit collaborator profile:

- forecasting/time-series evaluation background,
- experience with retail demand, intermittent demand, or benchmark design,
- comfort with meta-analysis or mixed-effects modeling,
- willingness to challenge the framing, not just proofread.

What to ask for:

- Is the claim scope appropriately limited?
- Are the benchmark aggregation choices defensible?
- Is the treatment of leakage/covariates strong enough?
- Which result should be the paper's central contribution?
- Which journal is realistic for the revised version?

Short outreach draft:

```text
Subject: Feedback request on retail demand forecasting benchmark/meta-analysis

Dear [Name],

I have published a v1.0 technical report on foundation models for retail demand
forecasting, combining a PRISMA-informed review, benchmark extraction, and
model-level meta-regression:

https://doi.org/10.5281/zenodo.21338004

I am preparing a shorter arXiv/journal version and would value a critical read
from someone with forecasting/time-series evaluation experience. The specific
questions are whether the benchmark aggregation is defensible, whether the
claims are scoped cautiously enough, and which result should be foregrounded for
a peer-reviewed submission.

If the topic is close to your interests, I would be grateful for either brief
feedback or a discussion about possible collaboration.

Best regards,
Maciej Rubczynski
```

## Stage 3: Journal Targeting

Recommended target order:

1. International Journal of Forecasting.
2. Machine Learning with Applications.
3. Data in Brief only as a possible companion data/reproducibility article, not
   as the main article.

### 1. International Journal of Forecasting

Fit: strongest intellectual fit if the revised article is framed around
forecasting evaluation, benchmark reliability, and decision guidance for retail
demand forecasting.

Why it is hard:

- It is the leading specialist forecasting venue.
- The paper must read as a forecasting contribution, not only an ML benchmark.
- Main text should be shorter and clearer than the current technical report.
- Claims about foundation models should be cautious and benchmark-specific.

Use if the paper is revised around:

- benchmark-level evidence,
- protocol and metric sensitivity,
- practical decision guidance,
- implications for forecasting evaluation.

Official reference:

- International Institute of Forecasters IJF page:
  <https://forecasters.org/ijf/>

### 2. Machine Learning with Applications

Fit: plausible if the revised article is framed as applied ML evidence about
foundation models in retail forecasting, with reproducible benchmark extraction
and practitioner cost-accuracy guidance.

Why it may be more realistic:

- Broader applied-ML scope.
- The foundation-model angle is central.
- The paper can emphasize empirical guidance and reproducibility.

Risk:

- It may be less natural than IJF for a systematic-review/meta-analysis-heavy
  forecasting paper.

Official reference:

- Machine Learning with Applications guide for authors:
  <https://www.sciencedirect.com/journal/machine-learning-with-applications/publish/guide-for-authors>

### 3. Data in Brief

Fit: only as a companion article if the extraction table and replication
materials become the primary contribution.

Why not the main target:

- The current work is a research synthesis and benchmark/meta-analysis, not just
  a data descriptor.
- The narrative contribution would need a separate journal/preprint home.

Official reference:

- Data in Brief aims and scope:
  <https://www.sciencedirect.com/journal/data-in-brief>

## Concrete Next Tasks

1. Create `paper/arxiv/` from the current LaTeX source.
2. Produce a shorter v1.1 outline:
   - Introduction: one page.
   - Related work: compressed.
   - Methods: keep only reproducibility-critical details.
   - Results: foreground three headline findings.
   - Discussion: focus on decision guidance and limitations.
   - Appendices: move long extraction and sensitivity material.
3. Build an arXiv source zip and test compilation from a clean directory.
4. Ask for one external review using the outreach draft above.
5. After feedback, decide between IJF and MLWA.
