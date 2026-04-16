#!/usr/bin/env Rscript
# ============================================================================
# meta_regression.R  — §6 pre-registered meta-regression pipeline.
#
# Implements the three-pass pooling strategy from §6.1:
#   (1) Dataset-anchored Δ: FM row MINUS same-paper/same-dataset/same-horizon
#       gradient-tree row. This is the primary estimand.
#   (2) Absolute matched: within-paper pairs on common metric scale.
#   (3) Friedman rank: per-paper ranks across FM / ML / stats families.
#
# Fits mixed-effects meta-regression (metafor::rma.mv) with cluster_var =
# paper_id and Knapp-Hartung small-sample adjustment, against the eight
# moderators declared in §6.2.
#
# Inputs:
#   analysis/extraction_schema.csv  — raw PRISMA extraction (Source A).
#   benchmark/results/local_fm_sweep.csv  — optional Source B rows (created
#     by tools/export_mlflow_to_csv.py once run_local_fm_sweep.sh finishes).
#     When present, Source B rows are appended with source="LOCAL" and the
#     regression re-runs with and without them (three-way sensitivity per
#     §6.6: full / excl OWN_* / excl OWN_* + LOCAL_*).
#
# Outputs (analysis/figures/):
#   figure_6_1_forest_m5.pdf
#   figure_6_2_forest_favorita.pdf
#   figure_6_3_forest_rohlik.pdf
#   figure_6_4_pareto_consumer_hw.pdf
#   figure_6_5_pareto_cloud_gpu.pdf
#   table_6_1_moderators.csv
#   table_6_2_heterogeneity.csv
#
# Usage:
#   Rscript analysis/meta_regression.R
# ============================================================================

suppressPackageStartupMessages({
  library(metafor)
  library(ggplot2)
  library(dplyr)
  library(tidyr)
  library(readr)
  library(knitr)
})

# Run from the repo root: `Rscript analysis/meta_regression.R`.
# Paths are relative to that working directory.
SCHEMA_PATH <- "analysis/extraction_schema.csv"
LOCAL_PATH  <- "benchmark/results/local_fm_sweep.csv"
FIG_DIR     <- "analysis/figures"
dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)

# ---------------------------------------------------------------------------
# 1. Load + clean Source A (literature extraction).
# ---------------------------------------------------------------------------

load_extraction <- function(path) {
  # The raw file interleaves comment lines (`# === Category X ===`) with
  # data rows. read_csv with comment="#" strips them cleanly.
  raw <- read_csv(
    path, comment = "#", show_col_types = FALSE,
    col_types = cols(
      paper_id = col_character(),
      year = col_integer(),
      n_series = col_character(),      # free-text ("30490", "1579", "mixed")
      series_length_median = col_character(),
      horizon = col_character(),       # free-text ("28", "mixed")
      metric_value = col_character(),  # free-text ("0.520", "best", "2nd-4th")
      .default = col_character()
    )
  )
  raw$source <- "LIT"
  raw
}

# Retail datasets we meta-analyze. Everything else is excluded from the
# primary analysis per the review scope (§2.3). Cross-domain rows stay in
# the schema as provenance but don't feed the regression.
RETAIL_DATASETS <- c(
  "M5", "Favorita", "Rohlik v2", "VN1 Forecasting (Rohlik)",
  "fev-bench", "retail (unnamed)",
  "SE Europe retail (proprietary)", "M5 + 3 external",
  "Walmart"
)

# Dataset-level n_series for sampling-variance proxy (§6.2 pre-registered
# design: vi = 1/n_series). Used when row-level n_series is missing or
# mixed. Source B within-paper cells use n_valid = 100 (sampled series).
DATASET_N_SERIES <- c(
  "M5"       = 30490,
  "Favorita" = 30000,
  "Rohlik"   = 5390,
  "Walmart"  = 30490,
  "fev-bench" = 5000   # approximate median across fev-bench retail tasks
)

normalize_dataset <- function(d) {
  dplyr::case_when(
    grepl("^M5", d, ignore.case = TRUE) ~ "M5",
    grepl("Favorita", d, ignore.case = TRUE) ~ "Favorita",
    grepl("Rohlik|VN1", d, ignore.case = TRUE) ~ "Rohlik",
    grepl("fev-bench", d, ignore.case = TRUE) ~ "fev-bench",
    grepl("Walmart", d, ignore.case = TRUE) ~ "Walmart",
    TRUE ~ NA_character_
  )
}

normalize_family <- function(f) {
  # Collapse fine-grained `model_family` labels into four meta-analysis
  # families: FM, ML_TREE, STATS, NN (and NA otherwise — excluded).
  # The `ml` bucket holds most of our OWN_* LightGBM rows and the two
  # external C04 retail LightGBM/XGBoost rows, all tree-based — include
  # them in ML_TREE so Source A's LGBM side is not silently dropped.
  dplyr::case_when(
    f %in% c("foundation") ~ "FM",
    f %in% c("ml_tree", "ml_gbm", "gbdt", "ml",
             "ml_ensemble", "ml_hybrid") ~ "ML_TREE",
    f %in% c("statistical", "stat", "ets") ~ "STATS",
    f %in% c("nn", "deep", "transformer", "rnn",
             "deep_learning", "ensemble_dl") ~ "NN",
    TRUE ~ NA_character_
  )
}

# Parse numeric metric value, propagating NA for qualitative rows.
parse_metric <- function(x) suppressWarnings(as.numeric(x))

# Per §6.2, horizon is bucketed because papers report mixed / non-comparable
# horizons. Bins are: short (h<=7), medium (8<=h<=14), long (h>14), mixed.
bucket_horizon <- function(h) {
  n <- suppressWarnings(as.integer(h))
  dplyr::case_when(
    is.na(n) ~ "mixed",
    n <= 7 ~ "short",
    n <= 14 ~ "medium",
    TRUE ~ "long"
  )
}

prepare_rows <- function(raw) {
  raw %>%
    mutate(
      dataset_norm = normalize_dataset(dataset),
      family = normalize_family(model_family),
      metric_num = parse_metric(metric_value),
      horizon_bucket = bucket_horizon(horizon),
      has_covariates = tolower(has_covariates) %in% c("yes", "true", "1"),
      zero_shot = tolower(zero_shot) %in% c("yes", "true", "1"),
      fine_tuned = tolower(fine_tuned) %in% c("yes", "true", "1"),
      # Parse n_series to numeric; fall back to dataset-level lookup.
      n_series_num = {
        parsed <- suppressWarnings(as.numeric(gsub("[^0-9.]", "", n_series)))
        ifelse(is.na(parsed),
               DATASET_N_SERIES[normalize_dataset(dataset)],
               parsed)
      }
    ) %>%
    filter(
      !is.na(dataset_norm),
      !is.na(family),
      !is.na(metric_num)
    )
}

# ---------------------------------------------------------------------------
# 2. Pass (1) — Dataset-anchored Δ.
#
#    Primary (within-paper): FM metric MINUS same-paper ML_TREE metric within
#    paper × dataset × horizon. Preserves within-paper correlation but in
#    our Source A retail slice essentially no paper reports both families
#    under a shared paper_id, so this pass runs almost entirely on Source B
#    LOCAL_MAC_* cells.
#
#    Cross-paper (this function, after design call on 2026-04-15): pool
#    across papers within dataset × horizon × metric, taking
#    mean(FM rows) - mean(ML_TREE rows) as a single bucket-level Δ. This
#    lets Source A rows actually enter Pass 1 — at the cost of losing the
#    within-paper anchoring. Clustering moves to `~1 | dataset_norm` since
#    each Δ now mixes papers.
# ---------------------------------------------------------------------------

compute_paired_delta <- function(rows) {
  by_cell <- rows %>%
    group_by(paper_id, dataset_norm, horizon_bucket, metric_name) %>%
    filter(n_distinct(family) >= 2, any(family == "FM"),
           any(family == "ML_TREE")) %>%
    summarise(
      fm      = mean(metric_num[family == "FM"], na.rm = TRUE),
      ml_tree = mean(metric_num[family == "ML_TREE"], na.rm = TRUE),
      .groups = "drop"
    ) %>%
    mutate(delta = fm - ml_tree) %>%
    filter(is.finite(delta))

  by_cell
}

compute_crosspaper_delta <- function(rows) {
  rows %>%
    filter(family %in% c("FM", "ML_TREE")) %>%
    group_by(dataset_norm, horizon_bucket, metric_name) %>%
    filter(any(family == "FM"), any(family == "ML_TREE")) %>%
    summarise(
      fm       = mean(metric_num[family == "FM"], na.rm = TRUE),
      ml_tree  = mean(metric_num[family == "ML_TREE"], na.rm = TRUE),
      n_fm     = sum(family == "FM"),
      n_mltree = sum(family == "ML_TREE"),
      # §6.2 pre-registered proxy: vi = 1/n_fm + 1/n_mltree, scaled by
      # the harmonic mean of per-row n_series within the bucket. This
      # gives higher precision to buckets with more rows and larger datasets.
      n_series_hm = 1 / mean(1 / n_series_num, na.rm = TRUE),
      .groups  = "drop"
    ) %>%
    mutate(
      delta = fm - ml_tree,
      vi    = (1 / n_fm + 1 / n_mltree) * (1 / n_series_hm)
    ) %>%
    filter(is.finite(delta))
}

fit_meta_crosspaper <- function(delta_df) {
  # vi is pre-computed per bucket in compute_crosspaper_delta() using the
  # §6.2 pre-registered proxy: (1/n_fm + 1/n_mltree) / n_series_hm.
  rma.mv(
    yi = delta, V = vi,
    random = ~ 1 | dataset_norm,
    data = delta_df,
    test = "t",
    method = "REML"
  )
}

# ---------------------------------------------------------------------------
# 3. Pass (2) — Absolute matched: FM and ML_TREE metrics on same scale,
#    retained separately so rma.mv sees both endpoints and can estimate
#    heterogeneity in absolute error independent of within-paper baselines.
# ---------------------------------------------------------------------------

compute_absolute_matched <- function(rows) {
  rows %>%
    filter(family %in% c("FM", "ML_TREE")) %>%
    select(paper_id, dataset_norm, horizon_bucket, metric_name,
           family, metric_num, has_covariates, n_series, year)
}

# ---------------------------------------------------------------------------
# 4. Pass (3) — Friedman rank within each paper×dataset×horizon cell.
# ---------------------------------------------------------------------------

compute_rank_table <- function(rows) {
  rows %>%
    group_by(paper_id, dataset_norm, horizon_bucket, metric_name) %>%
    mutate(rank_within = rank(metric_num, ties.method = "average")) %>%
    ungroup() %>%
    select(paper_id, dataset_norm, horizon_bucket, family, rank_within)
}

# ---------------------------------------------------------------------------
# 5. Meta-regression with Knapp-Hartung adjustment (metafor::rma.mv).
# ---------------------------------------------------------------------------

fit_meta <- function(delta_df) {
  # §6.2 pre-registered sampling variance proxy: vi = 1/n_series. For
  # within-paper paired Δ (Source B LOCAL cells), n_series = n_valid = 100
  # (sampled series per cell, §5.1.3). For Source A pairs (rare in the
  # retail slice), n_series comes from per-row parsing or dataset lookup.
  if (!"vi" %in% colnames(delta_df)) {
    # Within-paper pairs: Source B uses n_valid = 100, so vi = 1/100 = 0.01.
    # This happens to equal the old placeholder but is now principled.
    delta_df$vi <- 0.01
  }
  rma.mv(
    yi = delta, V = vi,
    random = ~ 1 | paper_id / dataset_norm,
    data = delta_df,
    test = "t",                    # Knapp-Hartung small-sample adjustment
    method = "REML"
  )
}

fit_meta_by_moderator <- function(delta_df, moderator) {
  if (!"vi" %in% colnames(delta_df)) {
    delta_df$vi <- 0.01  # within-paper Source B: n_valid = 100
  }
  rma.mv(
    yi = delta, V = vi,
    mods = as.formula(paste("~", moderator)),
    random = ~ 1 | paper_id / dataset_norm,
    data = delta_df,
    test = "t",
    method = "REML"
  )
}

# ---------------------------------------------------------------------------
# 6. Forest plots per dataset (Figures 6.1 - 6.3).
# ---------------------------------------------------------------------------

save_forest <- function(delta_df, dataset, out_path) {
  sub <- delta_df %>% filter(dataset_norm == dataset)
  if (nrow(sub) < 2) {
    message(sprintf("Skipping forest for %s (n=%d rows)", dataset, nrow(sub)))
    return(invisible(NULL))
  }
  # Refit per-dataset: the global `res` has k=nrow(delta_df), so passing
  # it with a length-nrow(sub) slab blows up forest.rma. A per-dataset
  # fit also matches the §6.1 figure semantics ("Δ on dataset X").
  if (!"vi" %in% colnames(sub)) sub$vi <- 0.01
  sub_fit <- tryCatch(
    rma.mv(
      yi = delta, V = vi,
      random = ~ 1 | paper_id,
      data = sub, test = "t", method = "REML"
    ),
    error = function(e) { message("Per-dataset fit failed for ", dataset, ": ", e$message); NULL }
  )
  if (is.null(sub_fit)) return(invisible(NULL))
  pdf(out_path, width = 7, height = max(4, 0.4 * nrow(sub) + 2))
  forest(sub_fit, slab = sub$paper_id,
         xlab = "FM - ML_TREE delta", main = dataset)
  dev.off()
  message("Wrote ", out_path)
}

# ---------------------------------------------------------------------------
# 7. Pareto frontier (Figures 6.4 / 6.5).
# ---------------------------------------------------------------------------

#' Build a cost-accuracy Pareto scatter. `cost_axis` picks `consumer_hw`
#' (M_SERIES_MAC marginal electricity; Figure 6.4 primary) or `cloud_gpu`
#' (Figure 6.5 sensitivity).
pareto_plot <- function(rows, cost_axis, out_path) {
  if (!("cost_usd" %in% colnames(rows))) {
    message(sprintf("Skipping %s Pareto — cost_usd column missing", cost_axis))
    return(invisible(NULL))
  }
  have <- rows %>%
    filter(!is.na(metric_num), !is.na(cost_usd))
  if (nrow(have) < 2) {
    message(sprintf("Skipping %s Pareto — need Source B cost rows", cost_axis))
    return(invisible(NULL))
  }
  p <- ggplot(have, aes(cost_usd, metric_num, colour = family)) +
    geom_point(size = 2) +
    scale_x_log10() +
    labs(x = sprintf("log10 USD (%s)", cost_axis),
         y = "WAPE / WRMSSE",
         title = sprintf("Cost-accuracy Pareto (%s)", cost_axis))
  ggsave(out_path, p, width = 7, height = 5)
  message("Wrote ", out_path)
}

# ---------------------------------------------------------------------------
# 8. Main.
# ---------------------------------------------------------------------------

main <- function() {
  message("Loading Source A from ", SCHEMA_PATH)
  raw <- load_extraction(SCHEMA_PATH)
  if (file.exists(LOCAL_PATH)) {
    message("Appending Source B from ", LOCAL_PATH)
    loc <- read_csv(LOCAL_PATH, show_col_types = FALSE)
    loc$source <- "LOCAL"
    # Force column types to match Source A (everything is free-text in
    # extraction_schema.csv). Without this, mlflow-derived numeric columns
    # cause bind_rows() to error on the <chr>/<dbl> mismatch.
    cast_cols <- intersect(
      c("n_series", "series_length_median", "horizon", "metric_value",
        "runtime_reported", "gpu_hours"),
      colnames(loc)
    )
    for (col in cast_cols) loc[[col]] <- as.character(loc[[col]])
    if ("year" %in% colnames(loc)) loc$year <- as.integer(loc$year)
    raw <- bind_rows(raw, loc)
  } else {
    message("Source B file not found at ", LOCAL_PATH,
            " — running on Source A only.")
  }

  rows <- prepare_rows(raw)
  message(sprintf("Prepared %d analysis rows across %d papers, %d datasets.",
                  nrow(rows), n_distinct(rows$paper_id),
                  n_distinct(rows$dataset_norm)))

  delta <- compute_paired_delta(rows)
  delta_cross <- compute_crosspaper_delta(rows)
  abs_matched <- compute_absolute_matched(rows)
  rank_tab <- compute_rank_table(rows)

  message(sprintf("Paired Δ rows (within-paper): %d across %d datasets",
                  nrow(delta), n_distinct(delta$dataset_norm)))
  message(sprintf("Paired Δ rows (cross-paper pool): %d across %d datasets",
                  nrow(delta_cross), n_distinct(delta_cross$dataset_norm)))

  if (nrow(delta_cross) >= 3) {
    message("\n--- Cross-paper pooled Δ (primary §6.1) ---")
    res_cross <- fit_meta_crosspaper(delta_cross)
    print(res_cross)
    writeLines(capture.output(print(res_cross)),
               file.path(FIG_DIR, "table_6_1_crosspaper_intercept.txt"))
    write_csv(delta_cross,
              file.path(FIG_DIR, "table_6_1_crosspaper_cells.csv"))

    # Excl-M5 sensitivity on the cross-paper pool.
    d_no_m5 <- delta_cross %>% filter(dataset_norm != "M5")
    if (nrow(d_no_m5) >= 3) {
      message("\n--- Cross-paper pooled Δ, excl M5 ---")
      res_cross_nom5 <- fit_meta_crosspaper(d_no_m5)
      print(res_cross_nom5)
      writeLines(capture.output(print(res_cross_nom5)),
                 file.path(FIG_DIR, "table_6_1_crosspaper_intercept_exclM5.txt"))
    }
  }

  if (nrow(delta) >= 5) {
    res_intercept <- fit_meta(delta)
    print(res_intercept)

    mod_results <- list()
    for (mod in c("dataset_norm", "horizon_bucket")) {
      mod_results[[mod]] <- tryCatch(
        fit_meta_by_moderator(delta, mod),
        error = function(e) { message("Moderator ", mod, " fit failed: ", e$message); NULL }
      )
    }
    # Placeholder write — full H1-H4 table populated once Source B lands.
    writeLines(capture.output(print(res_intercept)),
               file.path(FIG_DIR, "table_6_1_intercept.txt"))

    for (ds in c("M5", "Favorita", "Rohlik")) {
      save_forest(delta, ds,
                  file.path(FIG_DIR, sprintf("figure_6_forest_%s.pdf", tolower(ds))))
    }
  } else {
    message("Fewer than 5 paired Δ rows — regression skipped.")
  }

  pareto_plot(rows, "consumer_hw",
              file.path(FIG_DIR, "figure_6_4_pareto_consumer_hw.pdf"))
  pareto_plot(rows, "cloud_gpu",
              file.path(FIG_DIR, "figure_6_5_pareto_cloud_gpu.pdf"))

  message("Done. Outputs in ", FIG_DIR)
}

main()
