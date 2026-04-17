#!/usr/bin/env Rscript
# ============================================================================
# meta_regression.R  — §6 meta-regression pipeline (v2: model-level pooling).
#
# Restructured from bucket-level (k=10) to model-level paired comparisons
# (k≥50) using per-task per-model data from fev-bench and Source B.
#
# Unit of analysis: one row per (FM_i, baseline_j, task, metric) pair.
# Effect size: delta_ij = FM_metric - baseline_metric (absolute difference).
# Nesting: ~1 | dataset_norm / paper_id to account for dataset-level
# correlation and within-task clustering.
#
# Inputs:
#   analysis/extraction_schema.csv  — Source A (literature) + fev-bench rows.
#   benchmark/results/local_fm_sweep.csv  — Source B rows (when available).
#
# Outputs (analysis/figures/):
#   table_6_1_model_level_deltas.csv
#   table_6_2_heterogeneity.csv
#   table_6_3_moderators.csv
#   figure_6_1_forest_*.pdf
#   figure_6_4_pareto_consumer_hw.pdf
#   sensitivity_*.txt
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

SCHEMA_PATH <- "analysis/extraction_schema.csv"
LOCAL_PATH  <- "benchmark/results/local_fm_sweep.csv"
FIG_DIR     <- "analysis/figures"
dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)

# ---------------------------------------------------------------------------
# 1. Load + clean.
# ---------------------------------------------------------------------------

load_extraction <- function(path) {
  raw <- read_csv(
    path, comment = "#", show_col_types = FALSE,
    col_types = cols(
      paper_id = col_character(),
      year = col_integer(),
      n_series = col_character(),
      series_length_median = col_character(),
      horizon = col_character(),
      metric_value = col_character(),
      .default = col_character()
    )
  )
  raw$source <- "LIT"
  raw
}

# Retail datasets we meta-analyze.
RETAIL_DATASETS <- c(
  "M5", "Favorita", "Rohlik v2", "VN1 Forecasting (Rohlik)",
  "fev-bench", "retail (unnamed)", "Rossmann", "Walmart",
  "SE Europe retail (proprietary)", "M5 + 3 external",
  "Restaurant", "Hierarchical Sales", "Hermes", "Car Parts"
)

# Dataset-level n_series for variance proxy.
DATASET_N_SERIES <- c(
  "M5"       = 30490,
  "Favorita" = 30000,
  "Rohlik"   = 5390,
  "Walmart"  = 2936,
  "Car Parts" = 2674,
  "Rossmann" = 1115,
  "Restaurant" = 813,
  "Hierarchical Sales" = 118,
  "Hermes"   = 10000,
  "fev-bench" = 5000
)

# FM model scale (log10 params) for moderator analysis.
FM_LOG_PARAMS <- c(
  "Chronos-2"           = log10(120e6),    # ~8.08
  "TiRex"               = log10(35e6),     # ~7.54
  "TimesFM-2.5"         = log10(200e6),    # ~8.30
  "Moirai-2.0-Small"    = log10(11e6),     # ~7.04
  "Chronos-Bolt-Base"   = log10(46e6),     # ~7.66
  "Chronos-Bolt-Tiny"   = log10(9e6),      # ~6.95
  "TabPFN-TS"           = log10(12e6),     # ~7.08
  "Toto-1.0"            = log10(100e6),    # ~8.00
  "chronos_bolt_tiny"   = log10(9e6),
  "tirex"               = log10(35e6),
  "chronos2"            = log10(120e6),
  "moirai2"             = log10(11e6),
  "timesfm25"           = log10(200e6)
)

normalize_dataset <- function(d) {
  dplyr::case_when(
    # fev-bench per-task datasets
    grepl("fev-bench/m5_", d, ignore.case = TRUE) ~ "M5",
    grepl("fev-bench/favorita_", d, ignore.case = TRUE) ~ "Favorita",
    grepl("fev-bench/rohlik_", d, ignore.case = TRUE) ~ "Rohlik",
    grepl("fev-bench/rossmann", d, ignore.case = TRUE) ~ "Rossmann",
    grepl("fev-bench/walmart", d, ignore.case = TRUE) ~ "Walmart",
    grepl("fev-bench/restaurant", d, ignore.case = TRUE) ~ "Restaurant",
    grepl("fev-bench/hierarchical", d, ignore.case = TRUE) ~ "Hierarchical Sales",
    grepl("fev-bench/hermes", d, ignore.case = TRUE) ~ "Hermes",
    # GIFT-Eval Sales domain datasets
    grepl("GIFT-Eval.*Car Parts", d, ignore.case = TRUE) ~ "Car Parts",
    grepl("GIFT-Eval.*Hierarchical", d, ignore.case = TRUE) ~ "Hierarchical Sales",
    grepl("GIFT-Eval.*Restaurant", d, ignore.case = TRUE) ~ "Restaurant",
    # Legacy aggregate fev-bench rows
    grepl("^fev-bench$", d, ignore.case = TRUE) ~ "fev-bench",
    # Standard datasets
    grepl("^M5", d, ignore.case = TRUE) ~ "M5",
    grepl("Favorita", d, ignore.case = TRUE) ~ "Favorita",
    grepl("Rohlik|VN1", d, ignore.case = TRUE) ~ "Rohlik",
    grepl("Walmart", d, ignore.case = TRUE) ~ "Walmart",
    grepl("Rossmann", d, ignore.case = TRUE) ~ "Rossmann",
    TRUE ~ NA_character_
  )
}

normalize_family <- function(f) {
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

parse_metric <- function(x) suppressWarnings(as.numeric(x))

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
      n_series_num = {
        parsed <- suppressWarnings(as.numeric(gsub("[^0-9.]", "", n_series)))
        ifelse(is.na(parsed),
               DATASET_N_SERIES[normalize_dataset(dataset)],
               parsed)
      },
      # Model scale moderator (log10 params, FM only).
      model_scale = FM_LOG_PARAMS[model_name]
    ) %>%
    filter(
      !is.na(dataset_norm),
      !is.na(family),
      !is.na(metric_num)
    )
}

# ---------------------------------------------------------------------------
# 2. Model-level paired deltas (NEW — primary for k≥50).
#
# For each (paper_id × metric) group that contains both FM and ML_TREE rows,
# compute one delta per FM model: delta_i = FM_i_metric - mean(ML_TREE_metric).
# This is the new unit of analysis.
# ---------------------------------------------------------------------------

compute_model_level_delta <- function(rows) {
  # Within each paper_id (= task for fev-bench/GIFT-Eval, = dataset×horizon
  # for Source B), pair each FM row with the best available baseline.
  # Baseline priority: ML_TREE if present, else STATS.
  # This allows GIFT-Eval (STATS baselines) and fev-bench (ML_TREE baselines)
  # to both contribute paired comparisons.
  baseline_families <- c("ML_TREE", "STATS")

  by_group <- rows %>%
    filter(family %in% c("FM", baseline_families)) %>%
    group_by(paper_id, dataset_norm, horizon_bucket, metric_name) %>%
    filter(any(family == "FM"), any(family %in% baseline_families)) %>%
    ungroup()

  # Compute baseline per group: prefer ML_TREE, fall back to STATS.
  baselines <- by_group %>%
    filter(family %in% baseline_families) %>%
    group_by(paper_id, dataset_norm, horizon_bucket, metric_name) %>%
    summarise(
      baseline_metric = mean(metric_num, na.rm = TRUE),
      baseline_family = first(family),
      n_baseline = n(),
      baseline_n_series = mean(n_series_num, na.rm = TRUE),
      .groups = "drop"
    )

  # FM rows joined with their within-group baseline.
  fm_rows <- by_group %>%
    filter(family == "FM") %>%
    inner_join(baselines, by = c("paper_id", "dataset_norm",
                                  "horizon_bucket", "metric_name"))

  # Compute delta and variance proxy.
  fm_rows %>%
    mutate(
      delta = metric_num - baseline_metric,
      # Relative delta: (FM - baseline) / baseline. Used for moderator plots.
      delta_rel = ifelse(baseline_metric > 0,
                         (metric_num - baseline_metric) / baseline_metric,
                         NA_real_),
      # Variance proxy: 1/n_series for each side, summed.
      vi = (1 / pmax(n_series_num, 1)) + (1 / pmax(baseline_n_series, 1)),
      # Unique pair ID for clustering.
      pair_id = paste(paper_id, model_name, metric_name, sep = "__")
    ) %>%
    filter(is.finite(delta)) %>%
    select(pair_id, paper_id, dataset_norm, horizon_bucket, metric_name,
           model_name, model_scale, has_covariates, zero_shot,
           metric_num, baseline_metric, baseline_family,
           delta, delta_rel, vi, source,
           n_series_num, baseline_n_series)
}

# ---------------------------------------------------------------------------
# 3. Legacy bucket-level deltas (kept for backward compatibility / sensitivity).
# ---------------------------------------------------------------------------

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
      n_series_hm = 1 / mean(1 / n_series_num, na.rm = TRUE),
      .groups  = "drop"
    ) %>%
    mutate(
      delta = fm - ml_tree,
      vi    = (1 / n_fm + 1 / n_mltree) * (1 / n_series_hm)
    ) %>%
    filter(is.finite(delta))
}

# ---------------------------------------------------------------------------
# 4. Meta-regression fits.
# ---------------------------------------------------------------------------

fit_model_level <- function(delta_df) {
  # Primary model: model-level deltas with dataset-level nesting.
  # k = nrow(delta_df), typically ≥50 with fev-bench expansion.
  rma.mv(
    yi = delta, V = vi,
    random = ~ 1 | dataset_norm / paper_id,
    data = delta_df,
    test = "t",
    method = "REML"
  )
}

fit_model_level_mods <- function(delta_df, moderator) {
  rma.mv(
    yi = delta, V = vi,
    mods = as.formula(paste("~", moderator)),
    random = ~ 1 | dataset_norm / paper_id,
    data = delta_df,
    test = "t",
    method = "REML"
  )
}

# Legacy fits (bucket-level).
fit_meta_crosspaper <- function(delta_df) {
  rma.mv(
    yi = delta, V = vi,
    random = ~ 1 | dataset_norm,
    data = delta_df,
    test = "t",
    method = "REML"
  )
}

# ---------------------------------------------------------------------------
# 5. Forest plots.
# ---------------------------------------------------------------------------

save_forest <- function(delta_df, dataset, out_path) {
  sub <- delta_df %>% filter(dataset_norm == dataset)
  if (nrow(sub) < 2) {
    message(sprintf("Skipping forest for %s (n=%d rows)", dataset, nrow(sub)))
    return(invisible(NULL))
  }
  sub_fit <- tryCatch(
    rma.mv(
      yi = delta, V = vi,
      random = ~ 1 | paper_id,
      data = sub, test = "t", method = "REML"
    ),
    error = function(e) { message("Per-dataset fit failed for ", dataset, ": ", e$message); NULL }
  )
  if (is.null(sub_fit)) return(invisible(NULL))

  slab_labels <- paste0(sub$model_name, " (", sub$metric_name, ")")
  pdf(out_path, width = 8, height = max(4, 0.35 * nrow(sub) + 2))
  forest(sub_fit, slab = slab_labels,
         xlab = "FM - baseline delta", main = dataset)
  dev.off()
  message("Wrote ", out_path)
}

# ---------------------------------------------------------------------------
# 6. Pareto frontier.
# ---------------------------------------------------------------------------

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
# 7. Sensitivity analyses.
# ---------------------------------------------------------------------------

run_sensitivity <- function(delta_df, label, out_prefix) {
  if (nrow(delta_df) < 3) {
    message(sprintf("Sensitivity '%s': k=%d, skipped.", label, nrow(delta_df)))
    return(invisible(NULL))
  }
  message(sprintf("\n--- Sensitivity: %s (k=%d) ---", label, nrow(delta_df)))
  fit <- tryCatch(
    fit_model_level(delta_df),
    error = function(e) { message("  fit failed: ", e$message); NULL }
  )
  if (!is.null(fit)) {
    print(fit)
    writeLines(capture.output(print(fit)),
               file.path(FIG_DIR, paste0(out_prefix, ".txt")))
  }
  invisible(fit)
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

  # ---- Model-level deltas (PRIMARY, k≥50) ----
  model_delta <- compute_model_level_delta(rows)
  message(sprintf("\nModel-level Δ: %d pairs across %d datasets, %d unique FMs.",
                  nrow(model_delta), n_distinct(model_delta$dataset_norm),
                  n_distinct(model_delta$model_name)))

  # Write delta table for paper.
  write_csv(model_delta,
            file.path(FIG_DIR, "table_6_1_model_level_deltas.csv"))

  if (nrow(model_delta) >= 5) {
    message("\n--- Primary model-level fit (all metrics, all datasets) ---")
    res_primary <- fit_model_level(model_delta)
    print(res_primary)
    writeLines(capture.output(print(res_primary)),
               file.path(FIG_DIR, "table_6_1_primary_intercept.txt"))

    # Heterogeneity diagnostics.
    het_df <- data.frame(
      k = res_primary$k,
      estimate = res_primary$beta[1],
      se = res_primary$se,
      ci_lb = res_primary$ci.lb,
      ci_ub = res_primary$ci.ub,
      pval = res_primary$pval,
      QE = res_primary$QE,
      QEp = res_primary$QEp,
      sigma2_dataset = res_primary$sigma2[1],
      sigma2_paper = res_primary$sigma2[2]
    )
    write_csv(het_df, file.path(FIG_DIR, "table_6_2_heterogeneity.csv"))

    # Moderator analyses.
    mod_results <- list()
    moderators <- c("dataset_norm", "horizon_bucket", "metric_name")
    # model_scale only for FM rows that have it.
    if (any(!is.na(model_delta$model_scale))) {
      moderators <- c(moderators, "model_scale")
    }
    # baseline_family moderator (ML_TREE vs STATS) — if both types present.
    if ("baseline_family" %in% colnames(model_delta) &&
        n_distinct(model_delta$baseline_family) > 1) {
      moderators <- c(moderators, "baseline_family")
    }
    for (mod in moderators) {
      mod_results[[mod]] <- tryCatch(
        fit_model_level_mods(model_delta, mod),
        error = function(e) {
          message("Moderator ", mod, " failed: ", e$message)
          NULL
        }
      )
      if (!is.null(mod_results[[mod]])) {
        writeLines(capture.output(print(mod_results[[mod]])),
                   file.path(FIG_DIR, sprintf("moderator_%s.txt", mod)))
      }
    }

    # Forest plots per dataset.
    for (ds in unique(model_delta$dataset_norm)) {
      save_forest(model_delta, ds,
                  file.path(FIG_DIR, sprintf("figure_6_forest_%s.pdf",
                                              gsub(" ", "_", tolower(ds)))))
    }
  } else {
    message("Fewer than 5 model-level Δ rows — primary regression skipped.")
  }

  # ---- Sensitivity analyses ----

  # Excl-M5 (metric artefact sensitivity).
  run_sensitivity(
    model_delta %>% filter(dataset_norm != "M5"),
    "Excl M5", "sensitivity_excl_m5"
  )

  # WAPE-only (metric consistency).
  run_sensitivity(
    model_delta %>% filter(metric_name == "WAPE"),
    "WAPE only", "sensitivity_wape_only"
  )

  # SQL-only (fev-bench primary metric).
  run_sensitivity(
    model_delta %>% filter(metric_name == "SQL"),
    "SQL only", "sensitivity_sql_only"
  )

  # Source B only (own experiments).
  run_sensitivity(
    model_delta %>% filter(grepl("^LOCAL", source)),
    "Source B only", "sensitivity_source_b_only"
  )

  # Source A only (literature).
  run_sensitivity(
    model_delta %>% filter(source == "LIT"),
    "Source A only", "sensitivity_source_a_only"
  )

  # ---- Legacy bucket-level (for comparison with original k=10) ----
  delta_cross <- compute_crosspaper_delta(rows)
  if (nrow(delta_cross) >= 3) {
    message("\n--- Legacy cross-paper bucket Δ (k=", nrow(delta_cross), ") ---")
    res_cross <- fit_meta_crosspaper(delta_cross)
    print(res_cross)
    writeLines(capture.output(print(res_cross)),
               file.path(FIG_DIR, "legacy_crosspaper_intercept.txt"))
    write_csv(delta_cross,
              file.path(FIG_DIR, "legacy_crosspaper_cells.csv"))
  }

  # ---- Pareto plots ----
  pareto_plot(rows, "consumer_hw",
              file.path(FIG_DIR, "figure_6_4_pareto_consumer_hw.pdf"))
  pareto_plot(rows, "cloud_gpu",
              file.path(FIG_DIR, "figure_6_5_pareto_cloud_gpu.pdf"))

  # ---- Summary ----
  message("\n=== Summary ===")
  message(sprintf("Total analysis rows: %d", nrow(rows)))
  message(sprintf("Model-level Δ pairs (k): %d", nrow(model_delta)))
  message(sprintf("Datasets: %s", paste(unique(model_delta$dataset_norm), collapse=", ")))
  message(sprintf("FM models: %s", paste(unique(model_delta$model_name), collapse=", ")))
  message(sprintf("Metrics: %s", paste(unique(model_delta$metric_name), collapse=", ")))
  message(sprintf("Outputs in %s", FIG_DIR))
}

main()
