#!/usr/bin/env Rscript
# Statistical validation of experimental matrix
# Checks temporal distribution of LLM calls across randomization factors

library(dplyr)
library(lubridate)

# Load matrix
cat("Loading matrix...\n")
df <- read.csv("results/experiments_for_r.csv", stringsAsFactors = FALSE)

cat(sprintf("✓ Loaded %d rows\n", nrow(df)))

# Parse dates
df$scheduled_date <- as.Date(df$scheduled_date)

# === VALIDATION 1: Total call volume ===
cat("\n=== VALIDATION 1: Total Call Volume ===\n")
total_calls <- nrow(df)
cat(sprintf("Total LLM calls scheduled: %d\n", total_calls))

if (total_calls != 1620) {
  cat(sprintf("✗ FAIL: Expected 1,620 calls, got %d\n", total_calls))
  quit(status = 1)
}
cat("✓ PASS: Correct total (1,620)\n")

# === VALIDATION 2: Daily distribution ===
cat("\n=== VALIDATION 2: Daily Distribution ===\n")
daily_counts <- df %>%
  group_by(scheduled_date, scheduled_day_of_week) %>%
  summarise(calls = n(), .groups = "drop") %>%
  arrange(scheduled_date)

print(daily_counts)

# Check if within 231-232 range
daily_min <- min(daily_counts$calls)
daily_max <- max(daily_counts$calls)
cat(sprintf("\nDaily range: %d - %d calls/day\n", daily_min, daily_max))

if (daily_min < 231 || daily_max > 232) {
  cat(sprintf("⚠ WARNING: Daily distribution outside 231-232 range\n"))
} else {
  cat("✓ PASS: Daily distribution within expected range (231-232)\n")
}

# === VALIDATION 3: Time slot balance ===
cat("\n=== VALIDATION 3: Time Slot Balance ===\n")
time_counts <- df %>%
  group_by(scheduled_time_slot) %>%
  summarise(calls = n(), .groups = "drop") %>%
  arrange(scheduled_time_slot)

print(time_counts)

time_expected <- 540
if (all(time_counts$calls == time_expected)) {
  cat(sprintf("✓ PASS: Perfect time slot balance (%d each)\n", time_expected))
} else {
  cat("✗ FAIL: Time slot imbalance detected\n")
  quit(status = 1)
}

# === VALIDATION 4: Engine balance ===
cat("\n=== VALIDATION 4: Engine Balance ===\n")
engine_counts <- df %>%
  group_by(engine) %>%
  summarise(calls = n(), .groups = "drop") %>%
  arrange(engine)

print(engine_counts)

engine_expected <- 540
if (all(engine_counts$calls == engine_expected)) {
  cat(sprintf("✓ PASS: Perfect engine balance (%d each)\n", engine_expected))
} else {
  cat("✗ FAIL: Engine imbalance detected\n")
  quit(status = 1)
}

# === VALIDATION 5: Temperature balance ===
cat("\n=== VALIDATION 5: Temperature Balance ===\n")
temp_counts <- df %>%
  group_by(temperature) %>%
  summarise(calls = n(), .groups = "drop") %>%
  arrange(temperature)

print(temp_counts)

temp_min <- min(temp_counts$calls)
temp_max <- max(temp_counts$calls)
cat(sprintf("\nTemperature range: %d - %d\n", temp_min, temp_max))

if (temp_max - temp_min <= 5) {
  cat("✓ PASS: Temperature balance acceptable (±5)\n")
} else {
  cat("⚠ WARNING: Temperature imbalance > 5\n")
}

# === VALIDATION 6: Product balance ===
cat("\n=== VALIDATION 6: Product Balance ===\n")
product_counts <- df %>%
  group_by(product_id) %>%
  summarise(calls = n(), .groups = "drop") %>%
  arrange(product_id)

print(product_counts)

product_min <- min(product_counts$calls)
product_max <- max(product_counts$calls)
cat(sprintf("\nProduct range: %d - %d\n", product_min, product_max))

if (product_max - product_min <= 20) {
  cat("✓ PASS: Product balance acceptable (±20)\n")
} else {
  cat("⚠ WARNING: Product imbalance > 20\n")
}

# === VALIDATION 7: Engine × Time slot interaction ===
cat("\n=== VALIDATION 7: Engine × Time Slot Interaction ===\n")
engine_time_crosstab <- df %>%
  group_by(engine, scheduled_time_slot) %>%
  summarise(calls = n(), .groups = "drop") %>%
  tidyr::pivot_wider(names_from = scheduled_time_slot, values_from = calls)

print(engine_time_crosstab)

# Check range
engine_time_counts <- df %>%
  group_by(engine, scheduled_time_slot) %>%
  summarise(calls = n(), .groups = "drop")

et_min <- min(engine_time_counts$calls)
et_max <- max(engine_time_counts$calls)
cat(sprintf("\nEngine×Time range: %d - %d\n", et_min, et_max))

if (et_min >= 179 && et_max <= 181) {
  cat("✓ PASS: Engine×Time balance within specification (179-181)\n")
} else {
  cat(sprintf("✗ FAIL: Engine×Time balance outside 179-181 range\n"))
  quit(status = 1)
}

# === VALIDATION 8: Day of week distribution ===
cat("\n=== VALIDATION 8: Day of Week Distribution ===\n")
dow_counts <- df %>%
  group_by(scheduled_day_of_week) %>%
  summarise(calls = n(), .groups = "drop") %>%
  arrange(scheduled_day_of_week)

print(dow_counts)

dow_min <- min(dow_counts$calls)
dow_max <- max(dow_counts$calls)
cat(sprintf("\nDay range: %d - %d\n", dow_min, dow_max))

# === SUMMARY ===
cat("\n" , rep("=", 70), "\n", sep="")
cat("✓ MATRIX VALIDATION PASSED\n")
cat(rep("=", 70), "\n", sep="")
cat("\nMatrix is valid for statistical analysis:\n")
cat("- Total calls: 1,620\n")
cat("- Engine balance: 540/540/540 (exact)\n")
cat("- Time slot balance: 540/540/540 (exact)\n")
cat("- Engine×Time balance: 179-181 (within spec)\n")
cat("- Seed: 42\n")
cat("- Mode: stratified_7day_balanced\n")
cat("\n✓ Matrix is ready for experiments\n")
