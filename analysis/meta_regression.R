#!/usr/bin/env Rscript
# ============================================================================
# meta_regression.R  — §6 exploratory Source A reanalysis pipeline (v1.4).
#
# Restructured from bucket-level (k=10) to model-level paired comparisons
# (k≥50) using per-task per-model data from fev-bench and Source B.
#
# Unit of analysis: one row per (FM_i, task, metric), paired against a
# conventional baseline row in the same benchmark task.  The v1.4 primary
# descriptive comparator is the best available conventional baseline in the
# cell; average-baseline deltas are retained as a sensitivity artifact.
# Effect size: log_ratio_ij = log(FM_metric / baseline_metric).
# Negative values mean lower error/loss for the FM.  Absolute deltas are
# retained as descriptive fields only.
# The field vi is a precision/weight proxy based on recorded series counts,
# not a validated sampling variance for the log-ratio.  REML/CR2 outputs are
# therefore exploratory diagnostics only, not confirmatory meta-analysis.
#
# Source B is retained in the extracted delta table and in descriptive
# sensitivity outputs, but excluded from the primary inferential synthesis
# unless explicitly toggled.  The legacy Source B audit shows that local FM rows
# and Azure baseline rows are not consistently evaluated on the same
# row-level series/workload, and paired prediction errors are unavailable.
# The v1.4 matched-panel Source B repair is generated separately by
# analysis/source_b_paired_panel_report.py.
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
#   figure_6_4_cost_error_scatter_consumer_hw.pdf
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

HAS_CLUBSANDWICH <- requireNamespace("clubSandwich", quietly = TRUE)

SCHEMA_PATH    <- "analysis/extraction_schema.csv"
LOCAL_PATH     <- "benchmark/results/local_fm_sweep.csv"
BOOTSTRAP_PATH <- "analysis/figures/table_bootstrap_se.csv"
FIG_DIR        <- "analysis/figures"
dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)

INCLUDE_SOURCE_B_IN_PRIMARY <- FALSE

write_trimmed_lines <- function(x, path) {
  x <- sub("[[:space:]]+$", "", x)
  while (length(x) > 0 && x[length(x)] == "") {
    x <- x[-length(x)]
  }
  writeLines(x, path)
}

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

derive_suite_id <- function(paper_id, dataset, source) {
  dplyr::case_when(
    source == "LOCAL" | grepl("^LOCAL|^OWN", paper_id) ~ "SourceB",
    grepl("^B02_fev|fev-bench", paper_id) | grepl("fev-bench", dataset, ignore.case = TRUE) ~ "fev-bench",
    grepl("^B03_gift|^B01_gift|GIFT-Eval", paper_id) | grepl("GIFT-Eval", dataset, ignore.case = TRUE) ~ "GIFT-Eval",
    TRUE ~ "other"
  )
}

derive_study_id <- function(paper_id, authors, year, title, source) {
  raw <- dplyr::case_when(
    source == "LOCAL" | grepl("^LOCAL|^OWN", paper_id) ~ "source_b_gap_filling_experiments",
    grepl("^B02_fev", paper_id) ~ "shchur_2025_fev_bench",
    grepl("^B03_gift|^B01_gift", paper_id) ~ "aksu_2024_gift_eval",
    grepl("^C01_m5", paper_id) ~ "makridakis_2022_m5",
    TRUE ~ paste(authors, year, title, sep = "_")
  )
  tolower(gsub("_+$", "", gsub("^_+", "", gsub("[^A-Za-z0-9]+", "_", raw))))
}

derive_task_id <- function(suite_id, paper_id, dataset, dataset_variant,
                           dataset_norm, frequency, horizon, eval_method) {
  task_stub <- dplyr::case_when(
    suite_id %in% c("fev-bench", "GIFT-Eval", "SourceB") ~ paper_id,
    !is.na(dataset_variant) & dataset_variant != "" ~ paste(dataset, dataset_variant, sep = "_"),
    TRUE ~ paste(dataset_norm, frequency, horizon, eval_method, sep = "_")
  )
  tolower(gsub("_+$", "", gsub("^_+", "", gsub("[^A-Za-z0-9]+", "_", task_stub))))
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
      model_scale = FM_LOG_PARAMS[model_name],
      suite_id = derive_suite_id(paper_id, dataset, source),
      study_id = derive_study_id(paper_id, authors, year, title, source),
      task_id = derive_task_id(suite_id, paper_id, dataset, dataset_variant,
                               dataset_norm, frequency, horizon, eval_method)
    ) %>%
    filter(
      !is.na(dataset_norm),
      !is.na(family),
      !is.na(metric_num)
    )
}

# ---------------------------------------------------------------------------
# 2. Model-level paired log-ratios (primary).
#
# For each (paper_id × metric) group that contains both FM and conventional
# baseline rows, compute one delta per FM model:
# log_ratio_i = log(FM_i_metric / mean(available baseline metrics)).
# Raw deltas are retained for continuity checks, but the log-ratio is the
# primary estimand because SQL, WAPE, and MASE live on different scales.
# ---------------------------------------------------------------------------

load_bootstrap_se <- function(path = BOOTSTRAP_PATH) {
  if (!file.exists(path)) {
    message("Bootstrap SE file not found: ", path)
    return(NULL)
  }
  bse <- read_csv(path, show_col_types = FALSE) %>%
    mutate(
      dataset_norm = case_when(
        dataset == "m5"       ~ "M5",
        dataset == "favorita" ~ "Favorita",
        dataset == "rohlik"   ~ "Rohlik",
        TRUE ~ NA_character_
      ),
      horizon_bucket = case_when(
        horizon <= 7  ~ "short",
        horizon <= 14 ~ "medium",
        TRUE          ~ "long"
      )
    ) %>%
    select(dataset_norm, horizon_bucket, model_name = model,
           bootstrap_se) %>%
    filter(!is.na(dataset_norm))
  bse
}

compute_model_level_delta <- function(rows, bootstrap_se_df = NULL,
                                      baseline_strategy = c("average", "best")) {
  baseline_strategy <- match.arg(baseline_strategy)
  # Within each task_id (= task for fev-bench/GIFT-Eval, = dataset×horizon
  # for Source B), pair each FM row with conventional baselines. The primary
  # strategy uses the within-cell average of available conventional baselines.
  # The "best" sensitivity uses the lowest-error conventional baseline in the
  # same cell. This allows GIFT-Eval (STATS baselines), fev-bench
  # (ML_TREE/STATS baselines), and Source B (LightGBM + Seasonal Naive) to all
  # contribute paired comparisons.
  baseline_families <- c("ML_TREE", "STATS")

  by_group <- rows %>%
    filter(family %in% c("FM", baseline_families)) %>%
    group_by(task_id, dataset_norm, horizon_bucket, metric_name) %>%
    filter(any(family == "FM"), any(family %in% baseline_families)) %>%
    ungroup()

  baseline_rows <- by_group %>%
    filter(family %in% baseline_families) %>%
    group_by(task_id, dataset_norm, horizon_bucket, metric_name) %>%
    mutate(n_baseline_available = n()) %>%
    ungroup()

  if (baseline_strategy == "average") {
    baselines <- baseline_rows %>%
      group_by(task_id, dataset_norm, horizon_bucket, metric_name) %>%
      summarise(
        baseline_metric = mean(metric_num, na.rm = TRUE),
        baseline_family = first(family),
        n_baseline = n(),
        baseline_n_series = mean(n_series_num, na.rm = TRUE),
        .groups = "drop"
      )
  } else {
    baselines <- baseline_rows %>%
      group_by(task_id, dataset_norm, horizon_bucket, metric_name) %>%
      slice_min(metric_num, n = 1, with_ties = FALSE) %>%
      ungroup() %>%
      transmute(
        task_id, dataset_norm, horizon_bucket, metric_name,
        baseline_metric = metric_num,
        baseline_family = family,
        n_baseline = n_baseline_available,
        baseline_n_series = n_series_num
      )
  }

  # FM rows joined with their within-group baseline.
  fm_rows <- by_group %>%
    filter(family == "FM") %>%
    inner_join(baselines, by = c("task_id", "dataset_norm",
                                  "horizon_bucket", "metric_name"))

  # Compute log-ratio, descriptive delta, and variance proxy.
  result <- fm_rows %>%
    mutate(
      delta = metric_num - baseline_metric,
      log_ratio = ifelse(metric_num > 0 & baseline_metric > 0,
                         log(metric_num / baseline_metric),
                         NA_real_),
      # Relative delta: (FM - baseline) / baseline. Used for moderator plots.
      delta_rel = ifelse(baseline_metric > 0,
                         (metric_num - baseline_metric) / baseline_metric,
                         NA_real_),
      # Weight proxy: 1/n_series for each side, summed.  This is not a
      # sampling variance for the log-ratio because paired prediction-error
      # variances/covariances are unavailable in Source A.
      vi = (1 / pmax(n_series_num, 1)) + (1 / pmax(baseline_n_series, 1)),
      # Unique pair ID for clustering.
      pair_id = paste(task_id, model_name, metric_name, sep = "__"),
      cluster_id = task_id,
      is_source_b = source == "LOCAL",
      paired_inference_ok = source != "LOCAL",
      quality_flag = ifelse(
        source == "LOCAL",
        "Source B descriptive only: unmatched n_series/workload and no paired prediction-error covariance",
        "Source A benchmark extraction"
      )
    ) %>%
    filter(is.finite(log_ratio))

  # For Source B WAPE pairs: replace vi with bootstrap SE² if available.
  if (!is.null(bootstrap_se_df) && nrow(bootstrap_se_df) > 0) {
    result <- result %>%
      left_join(bootstrap_se_df,
                by = c("dataset_norm", "horizon_bucket",
                       "model_name" = "model_name"),
                suffix = c("", ".bse")) %>%
      mutate(
        vi = ifelse(source == "LOCAL" & metric_name == "WAPE" &
                      !is.na(bootstrap_se),
                    bootstrap_se^2,
                    vi)
      ) %>%
      select(-bootstrap_se)
  }

  result %>%
    select(pair_id, paper_id, study_id, suite_id, task_id, cluster_id,
           dataset_norm, horizon_bucket, metric_name,
           model_name, model_scale, has_covariates, zero_shot,
           metric_num, baseline_metric, baseline_family,
           log_ratio, delta, delta_rel, vi, source,
           is_source_b, paired_inference_ok, quality_flag,
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
      log_ratio = ifelse(fm > 0 & ml_tree > 0, log(fm / ml_tree), NA_real_),
      vi    = (1 / n_fm + 1 / n_mltree) * (1 / n_series_hm)
    ) %>%
    filter(is.finite(log_ratio))
}

# ---------------------------------------------------------------------------
# 4. Meta-regression fits.
# ---------------------------------------------------------------------------

fit_model_level <- function(delta_df) {
  # Primary model: model-level log-ratios with three-level random effects.
  # (1) ~1|suite_id/task_id: benchmark-suite and within-task clustering.
  # (2) ~1|model_name: non-independence of pairs from the same FM.
  # k = nrow(delta_df), typically ≥50 with fev-bench expansion.
  rma.mv(
    yi = log_ratio, V = vi,
    random = list(~ 1 | suite_id / task_id, ~ 1 | model_name),
    data = delta_df,
    test = "t",
    dfs = "contain",
    method = "REML"
  )
}

fit_model_level_mods <- function(delta_df, moderator) {
  rma.mv(
    yi = log_ratio, V = vi,
    mods = as.formula(paste("~", moderator)),
    random = list(~ 1 | suite_id / task_id, ~ 1 | model_name),
    data = delta_df,
    test = "t",
    dfs = "contain",
    method = "REML"
  )
}

fit_model_level_equal_weight <- function(delta_df) {
  # Robustness check for the sampling-variance proxy.  This keeps the same
  # random-effects structure but gives every paired comparison identical V.
  rma.mv(
    yi = log_ratio, V = rep(1, nrow(delta_df)),
    random = list(~ 1 | suite_id / task_id, ~ 1 | model_name),
    data = delta_df,
    test = "t",
    dfs = "contain",
    method = "REML"
  )
}

# Legacy fits (bucket-level).
fit_meta_crosspaper <- function(delta_df) {
  rma.mv(
    yi = log_ratio, V = vi,
    random = ~ 1 | dataset_norm,
    data = delta_df,
    test = "t",
    dfs = "contain",
    method = "REML"
  )
}

summarise_fit <- function(fit, label, delta_df) {
  pred <- tryCatch(predict(fit), error = function(e) NULL)
  data.frame(
    label = label,
    k = fit$k,
    estimate = as.numeric(fit$beta[1]),
    se = fit$se[1],
    ci_lb = fit$ci.lb[1],
    ci_ub = fit$ci.ub[1],
    pval = fit$pval[1],
    pi_lb = if (!is.null(pred) && "pi.lb" %in% names(pred)) pred$pi.lb[1] else NA_real_,
    pi_ub = if (!is.null(pred) && "pi.ub" %in% names(pred)) pred$pi.ub[1] else NA_real_,
    n_suite_clusters = n_distinct(delta_df$suite_id),
    n_task_clusters = n_distinct(delta_df$task_id),
    n_study_clusters = n_distinct(delta_df$study_id),
    stringsAsFactors = FALSE
  )
}

write_cluster_summary <- function(delta_df, out_path) {
  cluster_df <- data.frame(
    cluster_level = c("suite_id", "task_id", "study_id"),
    n_clusters = c(n_distinct(delta_df$suite_id),
                   n_distinct(delta_df$task_id),
                   n_distinct(delta_df$study_id)),
    stringsAsFactors = FALSE
  )
  write_csv(cluster_df, out_path)
}

write_cr2_table <- function(fit, delta_df, label, out_path,
                            cluster_var = "task_id") {
  if (!HAS_CLUBSANDWICH) {
    writeLines(
      c(
        sprintf("CR2 unavailable for %s.", label),
        "Install the R package 'clubSandwich' to reproduce cluster-robust inference.",
        sprintf("Requested cluster variable: %s; clusters observed: %d",
                cluster_var, n_distinct(delta_df[[cluster_var]]))
      ),
      out_path
    )
    return(invisible(NULL))
  }

  note <- "CR2 on primary crossed-random-effects model."
  cr2_fit <- fit
  cr2 <- tryCatch(
    clubSandwich::coef_test(
      cr2_fit,
      vcov = "CR2",
      cluster = delta_df[[cluster_var]]
    ),
    error = function(e) NULL
  )

  if (is.null(cr2)) {
    note <- paste(
      "CR2 on cluster-compatible sensitivity model.",
      "The primary model includes a crossed model_name random effect,",
      "which is not nested within this cluster variable."
    )
    cr2_fit <- tryCatch(
      rma.mv(
        yi = log_ratio, V = vi,
        random = as.formula(paste("~ 1 |", cluster_var)),
        data = delta_df,
        test = "t",
        dfs = "contain",
        method = "REML"
      ),
      error = function(e) {
        writeLines(
          c(sprintf("CR2-compatible fit failed for %s.", label), e$message),
          out_path
        )
        NULL
      }
    )
    if (is.null(cr2_fit)) return(invisible(NULL))
    cr2 <- tryCatch(
      clubSandwich::coef_test(
        cr2_fit,
        vcov = "CR2",
        cluster = delta_df[[cluster_var]]
      ),
      error = function(e) {
        writeLines(
          c(sprintf("CR2 failed for %s.", label), e$message),
          out_path
        )
        NULL
      }
    )
  }

  if (!is.null(cr2)) {
    write_trimmed_lines(c(
      sprintf("CR2 cluster-robust inference: %s", label),
      sprintf("cluster = %s; n_clusters = %d", cluster_var,
              n_distinct(delta_df[[cluster_var]])),
      note,
      capture.output(print(cr2))
    ), out_path)
  }
  invisible(cr2)
}

run_leave_one_out <- function(delta_df, var, out_path) {
  levels <- sort(unique(delta_df[[var]]))
  rows <- list()
  for (lv in levels) {
    sub <- delta_df %>% filter(.data[[var]] != lv)
    if (nrow(sub) < 5 || n_distinct(sub$task_id) < 2) next
    fit <- tryCatch(fit_model_level(sub), error = function(e) NULL)
    if (!is.null(fit)) {
      rows[[length(rows) + 1]] <- summarise_fit(fit, paste("omit", lv), sub)
    }
  }
  if (length(rows) > 0) write_csv(bind_rows(rows), out_path)
}

write_study_characteristics <- function(rows, out_path) {
  study_df <- rows %>%
    group_by(study_id, suite_id, source, authors, year, title, venue) %>%
    summarise(
      access_date = "2026-04-12",
      datasets = paste(sort(unique(na.omit(dataset_norm))), collapse = "; "),
      models = paste(sort(unique(na.omit(model_name))), collapse = "; "),
      metrics = paste(sort(unique(na.omit(metric_name))), collapse = "; "),
      n_result_rows = n(),
      provenance_note = case_when(
        first(suite_id) == "SourceB" ~ "Own gap-filling experiments; not counted as PRISMA included studies.",
        first(suite_id) == "fev-bench" ~ "Benchmark-suite extraction; clustered as fev-bench.",
        first(suite_id) == "GIFT-Eval" ~ "Benchmark-suite extraction; clustered as GIFT-Eval.",
        TRUE ~ "External publication/preprint extraction."
      ),
      risk_of_bias_note = case_when(
        first(suite_id) == "SourceB" ~ "Single-lab experiment; useful for gap filling, limited independent replication.",
        first(suite_id) %in% c("fev-bench", "GIFT-Eval") ~ "Many dependent benchmark tasks from one suite; handled with task/suite clustering.",
        TRUE ~ "Reported aggregate result; independence and protocol comparability may be limited."
      ),
      .groups = "drop"
    ) %>%
    arrange(suite_id, study_id)
  write_csv(study_df, out_path)
}

write_descriptive_summaries <- function(delta_df, prefix) {
  suite_metric <- delta_df %>%
    group_by(suite_id, metric_name) %>%
    summarise(
      k = n(),
      n_tasks = n_distinct(task_id),
      n_models = n_distinct(model_name),
      median_log_ratio = median(log_ratio, na.rm = TRUE),
      mean_log_ratio = mean(log_ratio, na.rm = TRUE),
      q25_log_ratio = quantile(log_ratio, 0.25, na.rm = TRUE),
      q75_log_ratio = quantile(log_ratio, 0.75, na.rm = TRUE),
      share_fm_better = mean(log_ratio < 0, na.rm = TRUE),
      median_ratio = exp(median_log_ratio),
      mean_ratio = exp(mean_log_ratio),
      .groups = "drop"
    ) %>%
    arrange(suite_id, metric_name)

  suite_overall <- delta_df %>%
    group_by(suite_id) %>%
    summarise(
      k = n(),
      n_tasks = n_distinct(task_id),
      n_metrics = n_distinct(metric_name),
      n_models = n_distinct(model_name),
      median_log_ratio = median(log_ratio, na.rm = TRUE),
      mean_log_ratio = mean(log_ratio, na.rm = TRUE),
      q25_log_ratio = quantile(log_ratio, 0.25, na.rm = TRUE),
      q75_log_ratio = quantile(log_ratio, 0.75, na.rm = TRUE),
      share_fm_better = mean(log_ratio < 0, na.rm = TRUE),
      median_ratio = exp(median_log_ratio),
      mean_ratio = exp(mean_log_ratio),
      .groups = "drop"
    ) %>%
    arrange(suite_id)

  metric_overall <- delta_df %>%
    group_by(metric_name) %>%
    summarise(
      k = n(),
      n_suites = n_distinct(suite_id),
      n_tasks = n_distinct(task_id),
      n_models = n_distinct(model_name),
      median_log_ratio = median(log_ratio, na.rm = TRUE),
      mean_log_ratio = mean(log_ratio, na.rm = TRUE),
      q25_log_ratio = quantile(log_ratio, 0.25, na.rm = TRUE),
      q75_log_ratio = quantile(log_ratio, 0.75, na.rm = TRUE),
      share_fm_better = mean(log_ratio < 0, na.rm = TRUE),
      median_ratio = exp(median_log_ratio),
      mean_ratio = exp(mean_log_ratio),
      .groups = "drop"
    ) %>%
    arrange(metric_name)

  write_csv(suite_metric,
            file.path(FIG_DIR, paste0(prefix, "_suite_metric_summary.csv")))
  write_csv(suite_overall,
            file.path(FIG_DIR, paste0(prefix, "_suite_overall_summary.csv")))
  write_csv(metric_overall,
            file.path(FIG_DIR, paste0(prefix, "_metric_summary.csv")))
}

write_pipeline_count_report <- function(raw, rows, delta_average, delta_best,
                                        delta_primary, out_path) {
  counts <- bind_rows(
    data.frame(stage = "raw_extraction_rows", n = nrow(raw)),
    data.frame(stage = "prepared_analysis_rows", n = nrow(rows)),
    data.frame(stage = "prepared_source_a_rows", n = sum(rows$source == "LIT")),
    data.frame(stage = "prepared_source_b_rows", n = sum(rows$source == "LOCAL")),
    data.frame(stage = "average_baseline_delta_pairs_all_sources", n = nrow(delta_average)),
    data.frame(stage = "best_baseline_delta_pairs_all_sources", n = nrow(delta_best)),
    data.frame(stage = "primary_best_baseline_source_a_pairs", n = nrow(delta_primary)),
    delta_primary %>%
      count(metric_name, name = "n") %>%
      transmute(stage = paste0("primary_pairs_metric_", metric_name), n),
    delta_primary %>%
      count(suite_id, name = "n") %>%
      transmute(stage = paste0("primary_pairs_suite_", suite_id), n)
  )
  write_csv(counts, out_path)
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
      yi = log_ratio, V = vi,
      random = ~ 1 | task_id,
      data = sub, test = "t", dfs = "contain", method = "REML"
    ),
    error = function(e) { message("Per-dataset fit failed for ", dataset, ": ", e$message); NULL }
  )
  if (is.null(sub_fit)) return(invisible(NULL))

  slab_labels <- paste0(sub$model_name, " (", sub$metric_name, ")")
  pdf(out_path, width = 8, height = max(4, 0.35 * nrow(sub) + 2))
  forest(sub_fit, slab = slab_labels,
         xlab = "log(FM metric / baseline metric)", main = dataset)
  dev.off()
  message("Wrote ", out_path)
}

# ---------------------------------------------------------------------------
# 6. Cost-error scatter.
# ---------------------------------------------------------------------------

cost_error_scatter <- function(rows, cost_axis, out_path) {
  if (!("cost_usd" %in% colnames(rows))) {
    message(sprintf("Skipping %s cost-error scatter — cost_usd column missing", cost_axis))
    return(invisible(NULL))
  }
  have <- rows %>%
    filter(!is.na(metric_num), !is.na(cost_usd), cost_usd > 0)
  if (nrow(have) < 2) {
    message(sprintf("Skipping %s cost-error scatter — need Source B cost rows", cost_axis))
    return(invisible(NULL))
  }
  # Use shape to distinguish hardware cost basis (MacBook vs Azure).
  has_hw <- "hardware" %in% colnames(have) && n_distinct(have$hardware) > 1
  if (has_hw) {
    p <- ggplot(have, aes(cost_usd, metric_num, colour = family, shape = hardware)) +
      geom_point(size = 2.5) +
      scale_x_log10() +
      labs(x = "Cost (USD, log scale)",
           y = "WAPE",
           colour = "Model family",
           shape = "Hardware")
  } else {
    p <- ggplot(have, aes(cost_usd, metric_num, colour = family)) +
      geom_point(size = 2.5) +
      scale_x_log10() +
      labs(x = "Cost (USD, log scale)",
           y = "WAPE",
           colour = "Model family")
  }
  p <- p + theme_minimal(base_size = 11)
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
    write_trimmed_lines(capture.output(print(fit)),
                        file.path(FIG_DIR, paste0(out_prefix, ".txt")))
  }
  invisible(fit)
}

run_equal_weight_sensitivity <- function(delta_df, label, out_prefix) {
  if (nrow(delta_df) < 3) {
    message(sprintf("Sensitivity '%s': k=%d, skipped.", label, nrow(delta_df)))
    return(invisible(NULL))
  }
  message(sprintf("\n--- Sensitivity: %s (k=%d) ---", label, nrow(delta_df)))
  fit <- tryCatch(
    fit_model_level_equal_weight(delta_df),
    error = function(e) { message("  fit failed: ", e$message); NULL }
  )
  if (!is.null(fit)) {
    print(fit)
    write_trimmed_lines(capture.output(print(fit)),
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
  message(sprintf("Prepared %d analysis rows across %d row IDs, %d studies, %d tasks, %d datasets.",
                  nrow(rows), n_distinct(rows$paper_id),
                  n_distinct(rows$study_id), n_distinct(rows$task_id),
                  n_distinct(rows$dataset_norm)))
  write_study_characteristics(rows, "analysis/study_characteristics.csv")

  # ---- Load bootstrap SEs for Source B (if available) ----
  bse_df <- load_bootstrap_se()

  # ---- Model-level deltas ----
  model_delta_average <- compute_model_level_delta(rows, bootstrap_se_df = bse_df,
                                                   baseline_strategy = "average")
  model_delta_best <- compute_model_level_delta(rows, bootstrap_se_df = bse_df,
                                                baseline_strategy = "best")
  model_delta_primary <- if (INCLUDE_SOURCE_B_IN_PRIMARY) {
    model_delta_best
  } else {
    model_delta_best %>% filter(paired_inference_ok)
  }
  message(sprintf("\nModel-level log-ratio: %d best-baseline pairs across %d datasets, %d tasks, %d unique FMs.",
                  nrow(model_delta_best), n_distinct(model_delta_best$dataset_norm),
                  n_distinct(model_delta_best$task_id),
                  n_distinct(model_delta_best$model_name)))
  message(sprintf("Primary descriptive log-ratio: %d best-baseline Source A pairs (Source B included: %s).",
                  nrow(model_delta_primary),
                  ifelse(INCLUDE_SOURCE_B_IN_PRIMARY, "yes", "no")))

  # Write delta tables for paper and audit.
  write_csv(model_delta_average,
            file.path(FIG_DIR, "table_6_1_model_level_deltas.csv"))
  write_csv(model_delta_average,
            file.path(FIG_DIR, "table_6_1_model_level_deltas_average_baseline.csv"))
  write_csv(model_delta_best,
            file.path(FIG_DIR, "table_6_1_model_level_deltas_best_baseline.csv"))
  write_csv(model_delta_primary,
            file.path(FIG_DIR, "table_6_1_primary_model_level_deltas.csv"))
  write_descriptive_summaries(model_delta_primary, "table_6_1_primary_best_baseline")
  write_pipeline_count_report(
    raw, rows, model_delta_average, model_delta_best, model_delta_primary,
    file.path(FIG_DIR, "pipeline_count_report.csv")
  )

  if (nrow(model_delta_primary) >= 5) {
    message("\n--- Exploratory heuristic-weight fit (best baseline; Source A only unless toggled) ---")
    res_primary <- fit_model_level(model_delta_primary)
    print(res_primary)
    write_trimmed_lines(capture.output(print(res_primary)),
                        file.path(FIG_DIR, "table_6_1_heuristic_weight_intercept.txt"))
    write_trimmed_lines(capture.output(print(res_primary)),
                        file.path(FIG_DIR, "table_6_1_primary_intercept.txt"))
    write_cluster_summary(model_delta_primary,
                          file.path(FIG_DIR, "table_6_1_cluster_counts.csv"))
    write_cr2_table(res_primary, model_delta_primary, "primary/task_id",
                    file.path(FIG_DIR, "table_6_1_primary_cr2_task.txt"),
                    "task_id")
    write_cr2_table(res_primary, model_delta_primary, "primary/suite_id",
                    file.path(FIG_DIR, "table_6_1_primary_cr2_suite.txt"),
                    "suite_id")
    write_cr2_table(res_primary, model_delta_primary, "primary/study_id",
                    file.path(FIG_DIR, "table_6_1_primary_cr2_study.txt"),
                    "study_id")

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
      sigma2_suite = res_primary$sigma2[1],
      sigma2_task = res_primary$sigma2[2],
      sigma2_model = res_primary$sigma2[3]
    )
    write_csv(het_df, file.path(FIG_DIR, "table_6_2_heterogeneity.csv"))

    metric_summaries <- list()
    for (metric in c("SQL", "WAPE", "MASE")) {
      sub <- model_delta_primary %>% filter(metric_name == metric)
      if (nrow(sub) >= 5) {
        fit <- tryCatch(fit_model_level(sub), error = function(e) NULL)
        if (!is.null(fit)) {
          metric_summaries[[metric]] <- summarise_fit(fit, metric, sub)
          write_cr2_table(fit, sub, paste0(metric, "/task_id"),
                          file.path(FIG_DIR, sprintf("sensitivity_%s_cr2_task.txt",
                                                     tolower(metric))),
                          "task_id")
        }
      }
    }
    if (length(metric_summaries) > 0) {
      write_csv(bind_rows(metric_summaries),
                file.path(FIG_DIR, "table_6_1_metric_specific.csv"))
    }

    # Moderator analyses.
    mod_results <- list()
    moderators <- c("dataset_norm", "horizon_bucket", "metric_name")
    # model_scale only for FM rows that have it.
    if (any(!is.na(model_delta_primary$model_scale))) {
      moderators <- c(moderators, "model_scale")
    }
    # baseline_family moderator (ML_TREE vs STATS) — if both types present.
    if ("baseline_family" %in% colnames(model_delta_primary) &&
        n_distinct(model_delta_primary$baseline_family) > 1) {
      moderators <- c(moderators, "baseline_family")
    }
    for (mod in moderators) {
      mod_results[[mod]] <- tryCatch(
        fit_model_level_mods(model_delta_primary, mod),
        error = function(e) {
          message("Moderator ", mod, " failed: ", e$message)
          NULL
        }
      )
      if (!is.null(mod_results[[mod]])) {
        write_trimmed_lines(capture.output(print(mod_results[[mod]])),
                            file.path(FIG_DIR, sprintf("moderator_%s.txt", mod)))
      }
    }

    # Forest plots per dataset.
    for (ds in unique(model_delta_primary$dataset_norm)) {
      save_forest(model_delta_primary, ds,
                  file.path(FIG_DIR, sprintf("figure_6_forest_%s.pdf",
                                              gsub(" ", "_", tolower(ds)))))
    }

    run_leave_one_out(model_delta_primary, "suite_id",
                      file.path(FIG_DIR, "sensitivity_leave_one_suite_out.csv"))
    run_leave_one_out(model_delta_primary, "task_id",
                      file.path(FIG_DIR, "sensitivity_leave_one_task_out.csv"))
    run_leave_one_out(model_delta_primary, "model_name",
                      file.path(FIG_DIR, "sensitivity_leave_one_model_out.csv"))
  } else {
    message("Fewer than 5 model-level Δ rows — primary regression skipped.")
  }

  # ---- Sensitivity analyses ----

  # Average conventional baseline per cell (less stringent comparator).
  run_sensitivity(
    model_delta_average %>% filter(paired_inference_ok),
    "Average conventional baseline per cell", "sensitivity_average_baseline"
  )

  # Excl-M5 (metric artefact sensitivity).
  run_sensitivity(
    model_delta_primary %>% filter(dataset_norm != "M5"),
    "Excl M5", "sensitivity_excl_m5"
  )

  # WAPE-only (metric consistency).
  run_sensitivity(
    model_delta_primary %>% filter(metric_name == "WAPE"),
    "WAPE only", "sensitivity_wape_only"
  )

  # SQL-only (fev-bench primary metric).
  run_sensitivity(
    model_delta_primary %>% filter(metric_name == "SQL"),
    "SQL only", "sensitivity_sql_only"
  )

  # MASE-only.
  run_sensitivity(
    model_delta_primary %>% filter(metric_name == "MASE"),
    "MASE only", "sensitivity_mase_only"
  )

  # Source B only (own experiments).
  run_sensitivity(
    model_delta_best %>% filter(grepl("^LOCAL", source)),
    "Source B descriptive only (unmatched workload audit flag)", "sensitivity_source_b_only"
  )

  # Source A only (literature).
  run_sensitivity(
    model_delta_best %>% filter(source == "LIT"),
    "Source A only", "sensitivity_source_a_only"
  )

  # Leave-one-suite-out checks for benchmark-suite dominance.
  run_sensitivity(
    model_delta_primary %>% filter(!grepl("^B02_fev", paper_id)),
    "Leave fev-bench out", "sensitivity_without_fev_bench"
  )
  run_sensitivity(
    model_delta_primary %>% filter(!grepl("^B03_gift", paper_id)),
    "Leave GIFT-Eval out", "sensitivity_without_gift_eval"
  )

  # Equal-weight robustness check for the vi proxy.
  run_equal_weight_sensitivity(
    model_delta_primary,
    "Equal-weight V", "sensitivity_equal_weight"
  )

  # ---- Legacy bucket-level (for comparison with original k=10) ----
  delta_cross <- compute_crosspaper_delta(rows)
  if (nrow(delta_cross) >= 3) {
    message("\n--- Legacy cross-paper bucket Δ (k=", nrow(delta_cross), ") ---")
    res_cross <- fit_meta_crosspaper(delta_cross)
    print(res_cross)
    write_trimmed_lines(capture.output(print(res_cross)),
                        file.path(FIG_DIR, "legacy_crosspaper_intercept.txt"))
    write_csv(delta_cross,
              file.path(FIG_DIR, "legacy_crosspaper_cells.csv"))
  }

  # ---- Funnel / Egger removed in v1.3 ----
  write_trimmed_lines(c(
    "Removed in v1.3.",
    "The vertical axis would use sqrt(1/n_FM + 1/n_baseline), which is a workload-count proxy rather than a sampling SE.",
    "The plot therefore diagnoses recorded task sizes, not publication bias or small-study asymmetry."
  ), file.path(FIG_DIR, "funnel_removed_v1.3.txt"))

  # ---- Cost-error scatter plots ----
  cost_error_scatter(rows, "consumer_hw",
                     file.path(FIG_DIR, "figure_6_4_cost_error_scatter_consumer_hw.pdf"))
  cost_error_scatter(rows, "cloud_gpu",
                     file.path(FIG_DIR, "figure_6_5_cost_error_scatter_cloud_gpu.pdf"))

  # ---- Summary ----
  message("\n=== Summary ===")
  message(sprintf("Total analysis rows: %d", nrow(rows)))
  message(sprintf("Model-level best-baseline Δ pairs (k): %d", nrow(model_delta_best)))
  message(sprintf("Primary Δ pairs (k): %d", nrow(model_delta_primary)))
  message(sprintf("Datasets: %s", paste(unique(model_delta_primary$dataset_norm), collapse=", ")))
  message(sprintf("FM models: %s", paste(unique(model_delta_primary$model_name), collapse=", ")))
  message(sprintf("Metrics: %s", paste(unique(model_delta_primary$metric_name), collapse=", ")))
  message(sprintf("Outputs in %s", FIG_DIR))
}

main()
