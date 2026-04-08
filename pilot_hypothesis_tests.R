#!/usr/bin/env Rscript
# Pilot Study Hypothesis Tests
# Testing RQs on 30-run pilot data

library(readr)
library(dplyr)

# Load data
data <- read_csv('results/pilot_for_r_analysis.csv')

cat("=========================================\n")
cat("PILOT STUDY HYPOTHESIS TESTS (n=30)\n")
cat("=========================================\n\n")

# ============================================
# RQ1: People-Pleasing Bias
# H0: Violation rate = 0% (LLMs are perfect)
# H1: Violation rate > 0% (LLMs generate violations)
# ============================================

cat("RQ1: PEOPLE-PLEASING BIAS\n")
cat("----------------------------------------\n")

# One-sample t-test: Are violation counts significantly > 0?
violation_test <- t.test(data$violation_count, mu = 0, alternative = "greater")

cat(sprintf("Mean violations per run: %.2f (SD=%.2f)\n",
            mean(data$violation_count),
            sd(data$violation_count)))
cat(sprintf("One-sample t-test (H0: violations = 0):\n"))
cat(sprintf("  t = %.3f, df = %d, p = %.4f\n",
            violation_test$statistic,
            violation_test$parameter,
            violation_test$p.value))

if (violation_test$p.value < 0.001) {
  cat("  ✓ REJECT H0: LLMs generate significant compliance violations (p < 0.001)\n\n")
} else {
  cat(sprintf("  Result: p = %.4f\n\n", violation_test$p.value))
}

# ============================================
# RQ2: Engine Comparison
# H0: No difference in violations across engines
# H1: Engines differ in violation rates
# ============================================

cat("RQ2: CROSS-ENGINE COMPARISON\n")
cat("----------------------------------------\n")

# Kruskal-Wallis test (non-parametric ANOVA)
engine_test <- kruskal.test(violation_count ~ engine, data = data)

cat("Violations by engine:\n")
engine_summary <- data %>%
  group_by(engine) %>%
  summarise(
    n = n(),
    mean = mean(violation_count),
    sd = sd(violation_count),
    median = median(violation_count)
  )
print(engine_summary)

cat(sprintf("\nKruskal-Wallis test:\n"))
cat(sprintf("  H = %.3f, df = %d, p = %.4f\n",
            engine_test$statistic,
            engine_test$parameter,
            engine_test$p.value))

if (engine_test$p.value < 0.05) {
  cat("  ✓ SIGNIFICANT: Engines differ in violation rates\n\n")

  # Post-hoc pairwise comparisons
  cat("  Post-hoc pairwise Mann-Whitney U tests:\n")
  engines <- unique(data$engine)
  for (i in 1:(length(engines)-1)) {
    for (j in (i+1):length(engines)) {
      test <- wilcox.test(
        data$violation_count[data$engine == engines[i]],
        data$violation_count[data$engine == engines[j]]
      )
      cat(sprintf("    %s vs %s: p = %.4f\n", engines[i], engines[j], test$p.value))
    }
  }
  cat("\n")
} else {
  cat("  No significant difference between engines\n\n")
}

# ============================================
# RQ3: Product Comparison
# H0: No difference in violations across products
# H1: Products differ in violation rates
# ============================================

cat("RQ3: CROSS-PRODUCT COMPARISON\n")
cat("----------------------------------------\n")

product_test <- kruskal.test(violation_count ~ product_id, data = data)

cat("Violations by product:\n")
product_summary <- data %>%
  group_by(product_id) %>%
  summarise(
    n = n(),
    mean = mean(violation_count),
    sd = sd(violation_count),
    median = median(violation_count)
  )
print(product_summary)

cat(sprintf("\nKruskal-Wallis test:\n"))
cat(sprintf("  H = %.3f, df = %d, p = %.4f\n",
            product_test$statistic,
            product_test$parameter,
            product_test$p.value))

if (product_test$p.value < 0.05) {
  cat("  ✓ SIGNIFICANT: Products differ in violation rates\n\n")
} else {
  cat("  No significant difference between products\n\n")
}

# ============================================
# Additional Analysis: API Latency
# ============================================

cat("ADDITIONAL: API LATENCY COMPARISON\n")
cat("----------------------------------------\n")

latency_test <- kruskal.test(api_latency_ms ~ engine, data = data)

cat("API latency by engine (ms):\n")
latency_summary <- data %>%
  group_by(engine) %>%
  summarise(
    n = n(),
    mean = mean(api_latency_ms),
    sd = sd(api_latency_ms),
    median = median(api_latency_ms)
  )
print(latency_summary)

cat(sprintf("\nKruskal-Wallis test:\n"))
cat(sprintf("  H = %.3f, df = %d, p = %.4f\n",
            latency_test$statistic,
            latency_test$parameter,
            latency_test$p.value))

if (latency_test$p.value < 0.05) {
  cat("  ✓ SIGNIFICANT: Engines differ in API latency\n\n")
} else {
  cat("  No significant difference in latency\n\n")
}

# ============================================
# Effect Sizes
# ============================================

cat("EFFECT SIZES\n")
cat("----------------------------------------\n")

# Violation rate effect size (Cohen's d vs. H0: violations = 0)
cohens_d <- mean(data$violation_count) / sd(data$violation_count)
cat(sprintf("Cohen's d (violations vs. 0): %.3f ", cohens_d))
if (abs(cohens_d) > 0.8) {
  cat("(Large effect)\n")
} else if (abs(cohens_d) > 0.5) {
  cat("(Medium effect)\n")
} else {
  cat("(Small effect)\n")
}

cat("\n=========================================\n")
cat("HYPOTHESIS TESTS COMPLETE\n")
cat("=========================================\n")
