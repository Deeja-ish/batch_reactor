# Findings Report - Batch Reactor Telemetry Audit
**Author:** Khadija
**Dataset:** .ms file (Parquet) - 2,009,978 rows raw, 1,999,980 rows after dedup
**Tools:** DuckDB + Parquet
**Date:** 2026-10-27

## 0. Executive Summary
- Raw rows: 2,009,978. Distinct batches: 11,110. After removing 9,998 exact duplicate pairs: 1,999,980 rows.
- 32 raw `reactor_id` labels -> 8 physical reactors (R1-R8), 4 spellings each.
- 14 raw `operator_shift` labels -> 4 groups at ~25% each (A, B, C, Night). Keep separate as 4 groups, not 3.
- 360 raw `catalyst_lot` labels -> 120 canonical lots (`LOT-<number>`).
- Units: pressure has 9 variants, temperature has 10 variants, each ~20% null (402,966 and 402,061 nulls). Multiple unit variants appear within batches (0% of batches have a single raw/cleaned unit variant; 56.68% of masked labels are recovered via dominant batch/reactor mode).
- Outliers must be evaluated AFTER unit conversion. Raw maxima (1281.55 temp, 1092.14 pressure, 490.41 rpm, 59.04 feed_rate) are on mixed units and are invalid.
- Missingness is uniform across reactors and shifts (4.1–4.6%) -> rules out a single hardware failure, though not proven completely random (pressure missingness spikes up to ~12% at the end of batches).
- Validation will use `GroupKFold` by `batch_id` to prevent target leakage across time-steps.

---

## 1. Count Reconciliation [BLOCKING ISSUE 1]

### 1.1 Batch Count
- Query: 
```sql
SELECT COUNT(DISTINCT batch_id) as distinct_batches, MAX(batch_id) as max_id, MAX(batch_id)+1 as max_plus_1, COUNT(*) as total FROM '{DATA_PATH}'
```
- Result: distinct = 11,110, max = 11,110, max+1 = 11,111
- Rows per batch: 
```sql
SELECT batch_id, COUNT(*) as all_batches FROM '{DATA_PATH}' GROUP BY batch_id ORDER BY all_batches DESC
```
- Finding: Average 180 rows/batch. Found 6,634 batches with rows > 180 vs 4,477 batches with 180 rows. This explains the 1,999,800 vs 1,999,980 difference = 180 extra rows (equivalent to 1 batch).
- Evidence: `../docs/01_batch_count.csv`

---

## 2. Reactor, Shift, Lot Standardization

### 2.1 reactor_id - 32 -> 8
- Raw variants example: `R1` (220k-229k), `r1` (8.1k-8.6k), `R-1` (8.1k-8.6k), `Reactor 1` (8.1k-8.6k) - pattern repeats across R1-R8.
- Query:
```sql
SELECT DISTINCT reactor_id, COUNT(*) AS counts_per_reactor
FROM '{DATA_PATH}'
WHERE reactor_id IS NOT NULL
GROUP BY reactor_id
```
- Evidence: `../docs/02_reactor_id_raw_counts.csv`
- Normalized: R1-R8, each ~245k-258k rows total.
- Cleaning rule: `UPPER(TRIM(REPLACE(REPLACE(REPLACE(reactor_id,'Reactor',''),'-',''),' ','')))`

### 2.2 operator_shift - 14 -> 4 (NOT 3)
- Raw variants: `A`, `a`, `'A '`, `'Shift A'`, `B`, `b`, `'Shift B'`, `C`, `c`, `'Shift C '`, `Night`, `night`, `'Night '`, `N`
- Volume: Each of A, B, C, Night = ~25% (~500k rows). If Night were merged into C, that combined shift would account for ~50% (~1.01M rows), which is operationally unlikely.
- Cleaning rule: Keep 4 canonical labels (`A`, `B`, `C`, `Night`) mapped via `LOWER(TRIM(operator_shift))`.
- Evidence: `../docs/02_shift_raw_counts.csv`

### 2.3 catalyst_lot - 360 -> 120
- Inconsistency: Raw labels use prefixes `l`, `L`, and `LOT-` rather than adhering strictly to the `LOT-<number>` standard.
- Evidence: `../docs/02_lot_mapping.csv`
```sql
WITH cleaned_catalyst_lot AS (
    SELECT DISTINCT catalyst_lot as original_column, 
    CASE 
        WHEN UPPER(catalyst_lot) LIKE 'LOT-%' THEN UPPER(catalyst_lot)
        WHEN UPPER(catalyst_lot) LIKE 'L%' THEN CONCAT('LOT-', SUBSTRING(catalyst_lot, 2, 100))
        ELSE CONCAT('LOT-', catalyst_lot) 
    END AS standazise_unique_catalyst
    FROM '{DATA_PATH}'
    WHERE catalyst_lot IS NOT NULL
)
SELECT 
    COUNT(DISTINCT original_column) AS count_before_cleaning,
    COUNT(DISTINCT standazise_unique_catalyst) AS count_of_cleaned_column
FROM cleaned_catalyst_lot;
```

---

## 3. Shift vs Yield - Batch-Level Analysis [BLOCKING ISSUE 2]

**The method used:**
```sql
WITH raw_cleaned AS (
    SELECT batch_id, TRIM(LOWER(operator_shift)) AS raw_shift, yield_pct 
    FROM '{DATA_PATH}'
),
batch_level AS (
    SELECT batch_id, 
    CASE 
        WHEN raw_shift IN ('a', 'shift a') THEN 'A'
        WHEN raw_shift IN ('b', 'shift b') THEN 'B'
        WHEN raw_shift IN ('c', 'shift c') THEN 'C'
        WHEN raw_shift IN ('n', 'night') THEN 'Night'
        ELSE raw_shift
    END AS shift,
    ANY_VALUE(yield_pct) AS yield_pct
    FROM raw_cleaned
    GROUP BY batch_id, shift
)
SELECT * FROM batch_level
```

**Results - Batch Level (n=11,110):**
| Shift Group | n batches | mean yield % | sd % | 95% CI | min | max |
|---|---|---|---|---|---:|---|
| A (A,a,A ,Shift A) | 2808 | 62.71 | 16.63 | [62.15, 63.38] | 0 | 97.30 |
| B (B,b,Shift B) | 2706 | 62.33 | 16.18 | [61.71, 62.93] | 0 | 95.74 |
| C (C,c,Shift C ) | 2784 | 62.30 | 16.77 | [61.69, 62.94] | 0 | 96.57 |
| Night (Night,night,Night ,N) | 2813 | 61.83 | 17.04 | [61.17, 62.43] | 0 | 94.35 |

**Statistical Test:**
- Test: Kruskal-Wallis H = 4.52, p = 0.21
- Pairwise A vs Night: Mann-Whitney U = 4076132.0, p = 0.037, Bonferroni corrected p = 0.22 (6 comparisons)
- Effect size: 0.88 percentage point spread. Is this surprising by chance?
  No, this spread is not surprising and is consistent with random chance. Overall, the Kruskal-Wallis test across all four shifts shows no statistically significant difference (H = 4.52, p = 0.21 > 0.05). While an unadjusted pairwise comparison between the highest shift (A) and lowest shift (Night) initially appears borderline significant (p = 0.037), applying the Bonferroni correction for all 6 possible shift comparisons raises the p-value to p = 0.22. This confirms that a 0.88 percentage point spread between the highest and lowest groups is well within normal random variation.
- Decision: Standardize strings into 4 clean groups and retain the column for completeness, noting that the yield spread across shifts is not statistically significant.
- Evidence: `../docs/03_yield_by_shift_batch.csv`, `../docs/03_yield_boxplot.png`

---

## 4. Shift Merging Decision [BLOCKING ISSUE 3]

- Dictionary states 3 shifts (Morning/A, Afternoon/B, Night/C), whereas the telemetry data shows 4 distinct groups at ~25% volume each.
- Timestamp mismatch check: 
```sql
SELECT timestamp::TIME, operator_shift FROM '{DATA_PATH}' WHERE operator_shift IN ('night','n') ORDER BY timestamp LIMIT 20
```
- Finding: `Night` and `N` appear throughout the day (e.g., at 02:00, 11:59, 13:05, 15:23, 17:04), proving that `operator_shift` represents a 4-crew rotation schedule rather than time-of-day clock windows.
- Decision: **KEEP 4 separate labels (A, B, C, Night) until further clarification from plant operations.**
- Evidence: `../docs/04_shift_vs_hour.png`

---

## 5. Unit Labels - Structure, Recovery, Validation [BLOCKING ISSUE 4 + Deliverable 4]

### 5.1 Raw State
- `pressure_unit`: 9 variants (`BAR`, `kPa`, `barg`, `bar`, `PSI`, `kpa`, `psi`, `psig`) + 402,966 nulls (20.04%)
- `temp_unit`: 10 variants (`C`, `c`, `°F`, `degC`, `kelvin`, `°C`, `F`, `K`, `degF`) + 402,061 nulls (20.00%)
- `temp_c`: 89,375 nulls (4.44%), `pressure_bar`: 86,910 nulls (4.32%)

### 5.2 Structure - Is unit constant within batch?
- Query: 
```sql 
WITH cleaned_data AS (
    SELECT batch_id, UPPER(TRIM(reactor_id)) AS reactor_id, {cleaned_sql_pressure} AS cleaned_pressure_unit, LOWER(TRIM(pressure_unit)) AS raw_pressure_unit 
    FROM '{DATA_PATH}' 
    WHERE batch_id IS NOT NULL
)
SELECT batch_id, COUNT(*) AS total_batch_count, COUNT(cleaned_pressure_unit) AS clean_pressure_unit_count, COUNT(DISTINCT cleaned_pressure_unit) AS distinct_cleaned_pressure_count, COUNT(DISTINCT raw_pressure_unit) AS raw_pressure_unit_count
FROM cleaned_data
WHERE batch_id IS NOT NULL
GROUP BY batch_id
```
- Result: 0% of batches have `distinct_pressure == 1`, 100% have `distinct_pressure > 1`, 0% have all nulls.
- Same per reactor? 
```sql 
SELECT UPPER(TRIM(reactor_id)) AS reactor_id, COUNT(DISTINCT {cleaned_sql_pressure}) AS distinct_cleaned_pressure_units, COUNT(DISTINCT LOWER(TRIM(pressure_unit))) AS raw_pressure_unit
FROM '{DATA_PATH}'
WHERE reactor_id IS NOT NULL
GROUP BY reactor_id
ORDER BY reactor_id
```
- Finding: 100% of batches and reactors have `distinct_pressure > 1`, showing that secondary unit labels (such as `kPa`, `psi`, `barg`) are mixed within individual batches alongside a primary dominant unit (`bar` / `C` at ~56.7%).
- Evidence: `../docs/05_unit_constancy_per_batch.csv`

### 5.3 Gauge vs Absolute - Does barg differ from bar?
- Real world: `bar_abs = barg + 1.01325`
- Query:
```sql 
SELECT 
    {cleaned_sql_pressure} AS cleaned_units,
    AVG(pressure_bar) AS mean_pressure,
    COUNT(*) AS n
FROM '{DATA_PATH}'
WHERE {cleaned_sql_pressure} IN ('bar', 'barg') AND pressure_unit IS NOT NULL
GROUP BY cleaned_units
```
- Result: mean `bar` = 1.7400, mean `barg` = 1.7139, difference = 0.0261 bar.
- Conclusion: The difference between `bar` and `barg` (0.0261 bar) is negligible and far below the physical 1.01325 bar atmospheric offset. This indicates that the logging software/operators used `bar` and `barg` interchangeably on the same absolute scale, so no +1.01325 bar offset should be added.
- Evidence: `../docs/05_pressure_unit_means.csv`

### 5.4 Recovery Method (What was done with 20% nulls)
- Method: For each row with a missing unit, assign the modal (most frequent) unit of its `batch_id`. If the entire batch is null, fallback to the modal unit of the normalized `reactor_id` (R1–R8), and finally to the global mode (`'bar'` / `'C'`).
- Code: `COALESCE(clean_unit, batch_mode_unit, reactor_mode_unit, 'bar')`

### 5.5 Validation of Recovery Method
- Method: Take rows where the unit IS known, randomly mask 20% to null, apply hierarchical mode recovery, and compute accuracy against the true labels.
- Query:
```sql
WITH cleaned_df AS (
    SELECT row_number() OVER() AS row_count,
    {cleaned_sql_pressure} AS true_unit,
    batch_id,
    REGEXP_REPLACE(UPPER(TRIM(reactor_id)), '[^R0-9]', '', 'g') AS reactor_id_norm,
    CASE WHEN random() < 0.20 THEN 1 ELSE 0 END AS is_masked
    FROM '{DATA_PATH}'
    WHERE pressure_unit IS NOT NULL
),
unmasked_pool AS (
    SELECT * FROM cleaned_df WHERE is_masked = 0
),
batch_model AS (
    SELECT batch_id, MODE(true_unit) AS batch_predicted_unit
    FROM unmasked_pool
    GROUP BY batch_id
),
reactor_model AS (
    SELECT reactor_id_norm, MODE(true_unit) AS reactor_predicted_unit
    FROM unmasked_pool
    GROUP BY reactor_id_norm
),
batch_reactor_df AS (
    SELECT c.row_count, c.batch_id, c.reactor_id_norm, c.true_unit, COALESCE(bm.batch_predicted_unit, rm.reactor_predicted_unit, 'bar') AS predicted_unit
    FROM cleaned_df AS c
    LEFT JOIN batch_model AS bm ON c.batch_id = bm.batch_id
    LEFT JOIN reactor_model AS rm ON c.reactor_id_norm = rm.reactor_id_norm
    WHERE c.is_masked = 1
)
SELECT true_unit, predicted_unit, COUNT(*) AS count
FROM batch_reactor_df 
GROUP BY true_unit, predicted_unit
ORDER BY true_unit, count DESC
```
- Result: Overall Accuracy = 56.68%. Because `bar` is the majority unit inside every batch (~56.7% of rows), batch-mode imputation always predicts `bar` (Precision for `bar` = 56.68%, while minority units `barg`, `kPa`, `psi`, `psig` are never predicted by the batch mode).
- Conclusion: Hierarchical mode imputation only achieves 56.68% accuracy because units vary at the row level within batches rather than being constant per batch. Better recovery requires inferring units from the numerical magnitude of `pressure_bar` and `temp_c` (e.g., values ~100x normal are `kPa`, values ~14.5x normal are `psi`, temperatures ~350 are `Kelvin`).
- Evidence: `../docs/05_unit_recovery_validation.csv`

---

## 6. Outliers - Correct Order of Operations [BLOCKING ISSUE 5]
```sql
CREATE VIEW corrected_data AS
WITH deduped AS (
    SELECT DISTINCT * FROM '{DATA_PATH}'
),
cleaned_labels AS (
    SELECT *, REGEXP_REPLACE(UPPER(TRIM(reactor_id)), '[^R0-9]', '', 'g') AS reactor_norm_id,
        CASE 
            WHEN LOWER(TRIM(pressure_unit)) IN ('bar') THEN 'bar'
            WHEN LOWER(TRIM(pressure_unit)) IN ('barg') THEN 'barg'
            WHEN LOWER(TRIM(pressure_unit)) IN ('kpa') THEN 'kpa'
            WHEN LOWER(TRIM(pressure_unit)) IN ('psi') THEN 'psi'
            WHEN LOWER(TRIM(pressure_unit)) IN ('psig') THEN 'psig'
            ELSE LOWER(TRIM(pressure_unit))
        END AS clean_pressure_unit,
        CASE 
            WHEN LOWER(TRIM(temp_unit)) IN ('c', 'degc', '°c') THEN 'C'
            WHEN LOWER(TRIM(temp_unit)) IN ('f', 'degf', '°f') THEN 'F'
            WHEN LOWER(TRIM(temp_unit)) IN ('k', 'kelvin') THEN 'Kelvin'
            ELSE LOWER(TRIM(temp_unit))
        END AS clean_temp_unit
    FROM deduped
), 
batch_model AS (
    SELECT batch_id, MODE(clean_pressure_unit) AS b_pressure_unit, MODE(clean_temp_unit) AS b_temp_unit FROM cleaned_labels GROUP BY batch_id
), 
reactor_model AS (
    SELECT reactor_norm_id, MODE(clean_pressure_unit) AS r_pressure_unit, MODE(clean_temp_unit) AS r_temp_unit FROM cleaned_labels GROUP BY reactor_norm_id
), 
cleaned_data AS (
    SELECT c.*, 
    COALESCE(c.clean_pressure_unit, bm.b_pressure_unit, rm.r_pressure_unit, 'bar') AS final_p_unit,
    COALESCE(c.clean_temp_unit, bm.b_temp_unit, rm.r_temp_unit, 'C') AS final_temp_unit
    FROM cleaned_labels c
    LEFT JOIN batch_model bm ON c.batch_id = bm.batch_id
    LEFT JOIN reactor_model rm ON c.reactor_norm_id = rm.reactor_norm_id
)
SELECT *, 
CASE 
    WHEN final_p_unit = 'barg' THEN pressure_bar
    WHEN final_p_unit = 'psi' THEN pressure_bar * 0.0689476
    WHEN final_p_unit = 'psig' THEN (pressure_bar * 0.0689476) + 1.01325
    WHEN final_p_unit = 'kpa' THEN pressure_bar / 100.0
    ELSE pressure_bar
END AS pressure_bar_abs,
CASE 
    WHEN final_temp_unit = 'Kelvin' THEN temp_c - 273.15
    WHEN final_temp_unit = 'F' THEN (temp_c - 32.0) * (5.0 / 9.0)
    ELSE temp_c
END AS temp_c_final
FROM cleaned_data
```

```sql 
SELECT 
    MIN(temp_c_final) AS min_temp,
    MAX(temp_c_final) AS max_temp,
    AVG(temp_c_final) AS avg_temp,
    SUM(CASE WHEN temp_c_final > 300 THEN 1 ELSE 0 END) AS temp_gt_300,
    SUM(CASE WHEN temp_c_final < -273.15 THEN 1 ELSE 0 END) AS temp_lt_negative,

    MIN(pressure_bar_abs) AS min_pressure,
    MAX(pressure_bar_abs) AS max_pressure,
    SUM(CASE WHEN pressure_bar_abs < 0 THEN 1 ELSE 0 END) AS press_lt_0,
    SUM(CASE WHEN pressure_bar_abs > 50 THEN 1 ELSE 0 END) AS press_gt_50,
    SUM(CASE WHEN pressure_bar_abs > 100 THEN 1 ELSE 0 END) AS press_gt_100,

    MIN(agitator_rpm) AS rpm_min,
    MAX(agitator_rpm) AS rpm_max,
    SUM(CASE WHEN agitator_rpm < 0 THEN 1 ELSE 0 END) AS rpm_lt_0,
    SUM(CASE WHEN agitator_rpm < 0 AND agitator_rpm >= -2 THEN 1 ELSE 0 END) AS rpm_small_neg,
    SUM(CASE WHEN agitator_rpm < -2 THEN 1 ELSE 0 END) AS rpm_large_neg,
      
    MIN(feed_rate) AS feed_min,
    MAX(feed_rate) AS feed_max
FROM corrected_data
```

After conversion to C and bar_abs (using recovery from Section 5):
| Metric | Value | Notes |
|---|---|---|
| `min_temp` | -1237.87 °C | Impossible (< -273.15 °C absolute zero) |
| `max_temp` | 1281.55 °C | Unconverted `K`/`F` among the 20% null-unit rows |
| `avg_temp` | 76.15 °C | Normal operating temperature |
| `temp_gt_300` | 7,400 rows | Implausible for this process (> 300 °C) |
| `temp_lt_negative` | 339 rows | Below absolute zero (< -273.15 °C) |
| `min_pressure` | -1136.65 bar | Impossible negative absolute pressure |
| `max_pressure` | 101,360.83 bar | High outliers / unlabelled `kPa`/`psi` rows |
| `press_lt_0` | 905 rows | Impossible negative pressure (< 0 bar) |
| `press_gt_50` | 71,002 rows | Extreme pressure or unlabelled `kPa`/`psi` |
| `press_gt_100` | 70,802 rows | Extreme pressure or unlabelled `kPa`/`psi` |
| `rpm_min` | -268.50 RPM | Sensor glitch |
| `rpm_max` | 490.41 RPM | Normal upper operating range |
| `rpm_lt_0` | 148 rows | Total negative RPM rows |
| `rpm_small_neg` | 3 rows | Only 3 rows in [-2, 0] -> **No zero-point drift** |
| `rpm_large_neg` | 145 rows | 145 of 148 negatives are < -2 RPM -> **True glitches** |
| `feed_min` | 41.20 | Normal operating range |
| `feed_max` | 59.04 | Normal operating range |

Planned cleaning: Mask impossible values to `NULL`, do NOT take absolute value (-691 °C is not +691 °C).
- `temp_c_final < -273.15` or `> 300` -> `NULL`
- `pressure_bar_abs < 0` or `> 50` -> `NULL` (or infer missing unit from value range first)
- `agitator_rpm < 0` -> `NULL` (Since 145 out of 148 negative RPM values are large negatives `< -2` and only 3 fall between `-2` and `0`, the zero-point drift hypothesis around `-0.45` is rejected; all negative RPMs are sensor glitches).

Evidence: `../docs/06_outliers_after_conversion.png`, `../docs/06_negative_distribution.csv`

---

## 7. Missingness, Time, Reactor Distributions [BLOCKING ISSUE 6]

### 7.1 By Reactor
- Consolidated R1-R8 each have ~245k-258k rows.
- Missing rates are uniform across reactors:
  - `temp_c`: 4.29–4.63% (total 89,375)
  - `pressure_bar`: 4.12–4.61% (86,910)
  - `agitator_rpm`: 3.80–3.90% (77,260)
  - `feed_rate`: 4.15–4.44% (86,418)
  - `ph`: 4.05–4.73% (85,292)
  - `temp_unit` & `pressure_unit`: ~20% uniformly
- Conclusion: Missingness is independent of reactor hardware (no single dead sensor). However, it is NOT proven completely random (MCAR). Confidence: High for reactor independence, Low for MCAR.
- Evidence: `../docs/07_missing_by_reactor.csv`

### 7.2 By Shift 
- A, B, C, Night each have ~500k rows, with missing rates uniform at 4.16–4.61%.
- Evidence: `../docs/07_missing_by_shift.csv`

### 7.3 By Time
- By month: 
```sql
SELECT 
    CAST(DATE_TRUNC('month', CAST(timestamp AS TIMESTAMP)) AS DATE) AS month, 
    COUNT(*) AS rows, 
    COUNT(DISTINCT batch_id) AS batches 
FROM corrected_data 
WHERE timestamp IS NOT NULL
GROUP BY month 
ORDER BY month
```
- By hour of day:
```sql
SELECT 
    EXTRACT('hour' FROM CAST(timestamp AS TIMESTAMP)) AS hour_of_day, 
    COUNT(*) AS rows,
    COUNT(DISTINCT batch_id) AS active_batches
FROM corrected_data 
WHERE timestamp IS NOT NULL
GROUP BY hour_of_day 
ORDER BY hour_of_day
```
- Finding: No shutdown months or volume drops were observed. Telemetry volume is steady across both months and all 24 hours of the day, confirming continuous 24/7 plant operation.
- Evidence: `../docs/07_volume_by_month.png`, `../docs/07_volume_by_hour.png`

### 7.4 Timestamp Integrity
- Ordering and Gaps: 
```sql 
WITH ordered AS (
    SELECT 
        batch_id,
        CAST(timestamp AS TIMESTAMP) AS ts,
        LAG(CAST(timestamp AS TIMESTAMP)) OVER (PARTITION BY batch_id ORDER BY CAST(timestamp AS TIMESTAMP)) AS prev_ts
    FROM corrected_data
    WHERE timestamp IS NOT NULL AND batch_id IS NOT NULL
)
SELECT 
    batch_id,
    prev_ts,
    ts,
    DATE_DIFF('minute', prev_ts, ts) AS gap_minutes
FROM ordered
WHERE ts <= prev_ts OR (ts - prev_ts) > INTERVAL 1 MINUTE
ORDER BY gap_minutes DESC
```
- Overlap:
```sql 
SELECT 
    reactor_norm_id, 
    DATE_TRUNC('minute', CAST(timestamp AS TIMESTAMP)) AS minute_ts, 
    COUNT(DISTINCT batch_id) AS active_batches
FROM corrected_data
WHERE reactor_norm_id IS NOT NULL AND timestamp IS NOT NULL
GROUP BY reactor_norm_id, minute_ts
HAVING active_batches > 1
ORDER BY active_batches DESC, minute_ts
```
- Finding: 
  - Rows with duplicate/zero-minute step (`gap <= 0`): 9,998 in raw data (0 after `SELECT DISTINCT` deduplication).
  - Gaps > 1 minute: 0
  - Gaps > 2 minutes: 0
  - Reactor overlap instances (`active_batches > 1`): 515,430 reactor-minutes where a single reactor ID is logged as running multiple batches at the exact same timestamp.
- Evidence: `../docs/07_timestamp_gaps.csv`, `../docs/07_reactor_overlap.csv`

### 7.5 Deeper Missingness
- Vs position in batch:
```sql
WITH positioned AS (
    SELECT 
        batch_id,
        ROW_NUMBER() OVER (PARTITION BY batch_id ORDER BY CAST(timestamp AS TIMESTAMP)) AS pos,
        CASE WHEN temp_c IS NULL THEN 1.0 ELSE 0.0 END AS temp_null,
        CASE WHEN pressure_bar IS NULL THEN 1.0 ELSE 0.0 END AS press_null
    FROM corrected_data
    WHERE batch_id IS NOT NULL AND timestamp IS NOT NULL
)
SELECT 
    pos,
    COUNT(*) AS n_batches_at_pos,
    AVG(temp_null) * 100 AS temp_miss_rate_pct,
    AVG(press_null) * 100 AS press_miss_rate_pct
FROM positioned
GROUP BY pos
ORDER BY pos
```
- Finding: Missingness for both temperature and pressure remains steady around 4–6% across the main batch duration, followed by a sharp spike in pressure missingness up to ~12% at the very end of the longest batches (steps > 180).
- Runs (Are nulls in streaks?): 
```sql
WITH numbered AS (
    SELECT 
        batch_id,
        CAST(timestamp AS TIMESTAMP) AS ts,
        temp_c,
        ROW_NUMBER() OVER (PARTITION BY batch_id ORDER BY CAST(timestamp AS TIMESTAMP)) AS rn_all,
        ROW_NUMBER() OVER (PARTITION BY batch_id, (temp_c IS NULL) ORDER BY CAST(timestamp AS TIMESTAMP)) AS rn_group
    FROM corrected_data
    WHERE batch_id IS NOT NULL AND timestamp IS NOT NULL
),
null_streaks AS (
    SELECT 
        batch_id,
        (rn_all - rn_group) AS streak_id,
        COUNT(*) AS run_length
    FROM numbered
    WHERE temp_c IS NULL
    GROUP BY batch_id, (rn_all - rn_group)
)
SELECT 
    run_length,
    COUNT(*) AS num_streaks,
    SUM(run_length) AS total_null_rows_in_this_length
FROM null_streaks
GROUP BY run_length
ORDER BY run_length
```
- Finding: 
  - % of nulls in runs >= 5 mins: 12.87%
  - % of nulls in runs >= 10 mins: 12.83%
  - Roughly 87% of missing values occur as isolated 1–4 minute dropouts (safe for linear interpolation), while ~12.83% occur in prolonged outages of 10+ minutes.
- Vs other columns correlation: 
```sql
SELECT 
    COUNT(*) AS total_rows,
    SUM(CASE WHEN temp_c IS NULL THEN 1 ELSE 0 END) AS temp_null_count,
    SUM(CASE WHEN pressure_bar IS NULL THEN 1 ELSE 0 END) AS press_null_count,
    SUM(CASE WHEN temp_c IS NULL AND pressure_bar IS NULL THEN 1 ELSE 0 END) AS both_null_count,
    CORR(CASE WHEN temp_c IS NULL THEN 1.0 ELSE 0.0 END, 
         CASE WHEN pressure_bar IS NULL THEN 1.0 ELSE 0.0 END) AS null_phi_correlation
FROM corrected_data
```
- Findings: 
| total_rows | temp_null_count | press_null_count | both_null_count | null_phi_correlation |
|---|---|---|---|---|
| 2,009,978 | 89,375 | 86,910 | 3,147 | -0.008515 |

This near-zero phi correlation (-0.0085) shows that missing values in temperature and pressure occur independently of one another rather than from simultaneous full-logger power failures.
- Evidence: `../docs/07_missing_by_position.png`, `../docs/07_missing_runs.csv`, `../docs/07_missing_correlation.csv`

---

## 8. Duplicates and Grain

- Exact duplicates: 9,998 rows duplicated (19,996 rows with `keep=False` -> exact pairs). Removal reduces row count from 2,009,978 to 1,999,980.
- Grain: Telemetry = 1 row per minute per `(batch_id, timestamp)`. Target = 1 `yield_pct` per `batch_id` (repeated across ~180 rows per batch, ranging from 0% to 97.3%).
- Implication: Feature engineering must aggregate the ~180 time-steps into a single row per `batch_id` (using summary statistics such as mean, SD, min, max, slope, and time-above-threshold), and cross-validation must split by `batch_id`.
- Query: 
```sql 
WITH raw_t AS (
    SELECT * FROM '{DATA_PATH}'
),
dedup_t AS (
    SELECT DISTINCT * FROM '{DATA_PATH}'
),
batch_summary AS (
    SELECT 
        batch_id,
        COUNT(*) AS rows_per_batch,
        COUNT(DISTINCT timestamp) AS distinct_timestamps,
        COUNT(DISTINCT yield_pct) AS distinct_yields_in_batch,
        MIN(yield_pct) AS yield_val
    FROM dedup_t
    WHERE batch_id IS NOT NULL
    GROUP BY batch_id
)
SELECT 
    (SELECT COUNT(*) FROM raw_t) AS total_raw_rows,
    (SELECT COUNT(*) FROM dedup_t) AS total_deduped_rows,
    (SELECT COUNT(*) FROM raw_t) - (SELECT COUNT(*) FROM dedup_t) AS exact_duplicate_rows_removed,
    COUNT(*) AS total_batches,
    AVG(rows_per_batch) AS avg_rows_per_batch,
    MIN(rows_per_batch) AS min_rows_per_batch,
    MAX(rows_per_batch) AS max_rows_per_batch,
    MAX(distinct_yields_in_batch) AS max_distinct_yields_per_batch,
    MIN(yield_val) AS min_batch_yield,
    MAX(yield_val) AS max_batch_yield
FROM batch_summary
```
- Evidence: `../docs/08_grain_check.csv`

---

## 9. Validation Design [Deliverable - 3 to 4 sentences required]

To prevent target leakage from `yield_pct` being repeated across ~180 minute-level rows per batch, we will partition the dataset using 5-fold `GroupKFold` grouped strictly by `batch_id` so that all telemetry from any given batch resides entirely in either the training fold or the validation fold. Minute-level time-series signals (`temp_c_final`, `pressure_bar_abs`, `agitator_rpm`, `feed_rate`, `ph`) will be aggregated into a single batch-level feature vector per `batch_id` ($n = 11,110$ batches), capturing summary statistics, temporal slopes, and missingness indicators. All preprocessing parameters—including unit imputation rules, physical outlier clipping bounds, and feature scalers—will be fitted exclusively on the training folds before transforming validation folds. Final model performance will be evaluated using batch-level Root Mean Squared Error (RMSE) and Mean Absolute Error (MAE) on `yield_pct`.

---

## 10. Unit Recovery Method Summary [Deliverable]

- **Method:** Missing `pressure_unit` and `temp_unit` labels (~20% of rows) were imputed hierarchically using the modal cleaned unit of the row's `batch_id`, falling back to the modal unit of the normalized `reactor_id` (R1–R8) and finally the global mode (`'bar'` and `'C'`).
- **Validation:** Masking 20% of known unit labels at random and applying this hierarchical mode recovery yielded an overall recovery accuracy of 56.68%, matching the baseline prevalence of the dominant `'bar'` and `'C'` units.
- **Limitation:** Because unit labels vary at the individual row level within the same batch (`distinct_pressure > 1` in 100% of batches), batch-mode imputation always predicts `'bar'`/`'C'` and misses minority units (`kPa`, `psi`, `F`, `Kelvin`), leaving ~7,400 temperature rows $>300\text{ }^\circ\text{C}$ and ~71,000 pressure rows $>50\text{ bar}$ that require range-based unit inference or outlier masking.

---

## 11. Anything I Could Not Explain [Deliverable]

- **Massive Reactor Timestamp Overlaps (515,430 reactor-minutes):** Reactors R1–R8 frequently show multiple distinct `batch_id`s running simultaneously at the exact same minute. Physically, a single batch reactor vessel cannot process two separate chemical batches at once, suggesting either synthetic timestamp generation, clock desynchronization across loggers, or misassigned reactor IDs.
- **Row-Level Unit Switching Within Batches:** Rather than a sensor remaining locked to a single engineering unit (`bar` or `psi`) for the duration of a batch, every single batch contains a mixture of unit strings alongside 20% nulls, causing 7,400 temperature rows and ~71,000 pressure rows to remain out of physical bounds when imputed via batch mode.
- **End-of-Batch Pressure Missingness Spike (~12%) & 10+ Minute Sensor Dropouts (12.83%):** While temperature and pressure nulls are uncorrelated ($\phi = -0.0085$) and stay near ~4.4% for most of a batch, pressure missingness doubles to ~12% at the end of batches (step > 180), and 12.83% of temperature nulls occur in continuous streaks of 10+ minutes without any logged maintenance events.

---

## 12. Confidence and Limitations

- **High confidence:** Entity standardization (`reactor_id` 32 -> 8, `catalyst_lot` 360 -> 120, `operator_shift` 14 -> 4), exact duplicate removal (9,998 pairs), batch-level shift yield analysis showing no statistically significant shift effect ($H = 4.52, p = 0.21$), and proof that `bar` and `barg` share the same numerical scale (0.026 bar difference).
- **Medium confidence:** Crew-rotation interpretation of the 4 operator shifts (`A`, `B`, `C`, `Night`), and rejection of the RPM zero-point drift hypothesis (since 145 of 148 negative RPM values are large glitches $< -2\text{ RPM}$ and only 3 values lie in $[-2, 0]$).
- **Low confidence / Not proven:** Batch-mode unit recovery (56.68% accuracy is insufficient for minority units in the 20% null subset without range-based unit inference), and Missing Completely at Random (MCAR) assumptions given the 12.83% multi-minute dropout streaks and end-of-batch missingness spike.
- **Limitations:** Without external plant logs or a physical process specification sheet, we cannot resolve why a single reactor logs multiple concurrent batches (515,430 overlapping reactor-minutes) or definitively distinguish between genuine extreme pressure/temperature spikes and unlabelled `kPa`/`psi`/`Kelvin` rows among the 20% missing unit records.
