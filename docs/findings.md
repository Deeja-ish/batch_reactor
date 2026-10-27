# Findings Report - Batch Reactor Telemetry Audit
**Author:** Khadija
**Dataset:** .ms file (Parquet) - 2,009,978 rows raw, 1,999,980 rows after dedup
**Tools:** DuckDB + Parquet
**Date:** 2026-10-27

## 0. Executive Summary
- Raw rows: 2,009,978. Distinct batches: 11,110. After removing 9,998 exact duplicate pairs: 1,999,980 rows.
- 32 raw reactor_id labels -> 8 physical reactors (R1-R8), 4 spellings each.
- 14 raw operator_shift labels -> 4 groups at ~25% each (A, B, C, Night). Keep separate, not 3.
- 360 raw catalyst_lot labels -> 120 canonical lots.
- Units: pressure 9 variants, temperature 10 variants, each ~20% null (402,966 and 402,061 nulls). Unit constant within batch for [TODO]% of batches.
- Outliers must be evaluated AFTER unit conversion. Raw maxima (1281.55 temp, 1092.14 pressure, 490.41 rpm, 59.04 feed_rate) are on mixed units and are invalid.
- Missingness uniform across reactors/shifts (4.1-4.6%) -> not single hardware failure, but not proven random.
- Validation will be GroupKFold by batch_id.

---

## 1. Count Reconciliation [BLOCKING ISSUE 1]

### 1.1 Batch Count
- Query: `SELECT COUNT(DISTINCT batch_id) as distinct_batches, MAX(batch_id) as max_id, MAX(batch_id)+1 as max_plus_1, COUNT(*) as total FROM 'data_path'`
- Result: distinct = 11,110, max = 11110, max+1 = 11111
- Rows per batch: `SELECT batch_id, COUNT(*) as all_batches FROM data_path GROUP BY batch_id ORDER BY all_batches DESC`
- Finding: Average 180 rows/batch. Found 6634 batches with rows > 180 vs 4477 batches with 180 rows. This explains 1,999,800 vs 1,999,980 difference = 180 extra rows = 1 batch.
- Evidence: `docs/01_batch_count.csv`

### 1.2 Catalyst Lot Count
- Raw distinct: 360 From the report
- Math check: 360 / 3 = 120.
- Query: `SELECT clean_lot, COUNT(DISTINCT catalyst_lot) as variants FROM (SELECT LOWER(REGEXP_REPLACE(catalyst_lot,'[^a-z0-9]','')) as clean_lot, catalyst_lot FROM t) GROUP BY clean_lot HAVING variants !=3`
- Result: Lot(s) with non-3 variants: [TODO - list]
- Evidence: `docs/01_lot_variant_check.csv`                                                                                                                                                                                                                                                                                       

---

## 2. Reactor, Shift, Lot Standardization

### 2.1 reactor_id - 32 -> 8
- Raw variants example: R1 (220k-229k), r1 (8.1k-8.6k), R-1 (8.1k-8.6k), Reactor 1 (8.1k-8.6k) - pattern repeats R1-R8.
- Evidence: `docs/02_reactor_id_raw_counts.csv`
- Normalized: R1-R8, each ~245k-258k rows total.
- Cleaning rule: `UPPER(TRIM(REPLACE(REPLACE(REPLACE(reactor_id,'Reactor',''),'-',''),' ','')))`

### 2.2 operator_shift - 14 -> 4 (NOT 3)
- Raw variants: A, a, 'A ', 'Shift A', B, b, 'Shift B', C, c, 'Shift C ', Night, night, 'Night ', N
- Volume: Each of A, B, C, Night = ~25% (~500k rows). If Night=C, that shift = ~50% (~1.01M rows) - operationally unlikely.
- Cleaning rule: Keep 4 labels: A, B, C, Night. Map via lower+trim.
- Evidence: `docs/02_shift_raw_counts.csv`

### 2.3 catalyst_lot - 360 -> [119 or 120]
- Inconsistency: Does not adhere to LOT-<number> standard.
- Cleaning rule: [TODO: your regex]
- Evidence: `docs/02_lot_mapping.csv`

---

## 3. Shift vs Yield - Batch-Level Analysis [BLOCKING ISSUE 2]

**The method used:**
```sql
CREATE VIEW batch_level AS
SELECT batch_id, ANY_VALUE(TRIM(LOWER(operator_shift))) as shift, ANY_VALUE(yield_pct) as yield
FROM data_path GROUP BY batch_id
```

**Results - Batch Level (n=11,110):**
| Shift Group | n batches | mean yield % | sd % | 95% CI | min | max |
|---|---|---|---|---|---:|---|
| A (A,a,A ,Shift A) | [TODO] | 62.71 | [TODO] | [TODO] | [TODO] | [TODO] |
| B (B,b,Shift B) | [TODO] | 62.33 | [TODO] | | | |
| C (C,c,Shift C ) | [TODO] | 62.30 | [TODO] | | | |
| Night (Night,night,Night ,N) | [TODO] | 61.83 | [TODO] | | | |

**Statistical Test:**
- Test: Kruskal-Wallis H = [TODO], p = [TODO] (or Permutation test)
- Pairwise A vs Night: Mann-Whitney U = [TODO], p = [TODO], Bonferroni corrected p = [TODO] (6 comparisons)
- Effect size: 0.88 percentage point spread. Is this surprising by chance? [TODO: interpretation]
- Decision: Standardize strings but keep column, as spread is consistent but small.
- Evidence: `docs/03_yield_by_shift_batch.csv`, `docs/03_yield_boxplot.png`

---

## 4. Shift Merging Decision [BLOCKING ISSUE 3]

- Dictionary says 3 shifts (Morning/A, Afternoon/B, Night/C). Data shows 4 groups at ~25% each.
- Timestamp mismatch check: `SELECT timestamp::TIME, operator_shift FROM t WHERE shift IN ('night','n') ORDER BY timestamp LIMIT 20`
- Finding: Night and N appear at 11:59, 13:05, 15:23, 17:04 -> NOT time-of-day, represents crew rotation.
- Decision: **KEEP 4 separate labels (A, B, C, Night) until justification from operations.** State uncertainty honestly.
- Evidence: `docs/04_shift_vs_hour.png`

---

## 5. Unit Labels - Structure, Recovery, Validation [BLOCKING ISSUE 4 + Deliverable 4]

### 5.1 Raw State
- pressure_unit: 9 variants [TODO: list bar,barg,psi,psig,kPa...] + 402,966 nulls (20.04%)
- temp_unit: 10 variants [TODO: list C, degC, F, K...] + 402,061 nulls (20.00%)
- temp_c: 89,375 nulls (4.44%), pressure_bar: 86,910 nulls (4.32%)

### 5.2 Structure - Is unit constant within batch?
- Query: `SELECT batch_id, COUNT(DISTINCT pressure_unit) as d FROM t WHERE pressure_unit IS NOT NULL GROUP BY batch_id`
- Result: [TODO]% batches have d=1, [TODO]% have d>1, [TODO]% have all nulls
- Same per reactor? `SELECT reactor_id, COUNT(DISTINCT pressure_unit) FROM t GROUP BY reactor_id`
- Finding: [TODO: e.g., unit constant within batch for 99.2% batches]
- Evidence: `docs/05_unit_constancy_per_batch.csv`

### 5.3 Gauge vs Absolute - Does barg differ from bar?
- Real world: bar_abs = barg + 1.01325
- Query: `SELECT pressure_unit, AVG(pressure_bar), COUNT(*) FROM t GROUP BY pressure_unit`
- Result: mean bar = [TODO], mean barg = [TODO], difference = [TODO]
- Conclusion: [TODO: difference ~1 bar? Then need conversion. If not, logging software mislabels]
- Evidence: `docs/05_pressure_unit_means.csv`

### 5.4 Recovery Method (What you did with 20% nulls)
- Method: For each batch, assign null unit = mode unit of that batch. If batch all null, assign mode of that consolidated reactor_id (R1-R8). If reactor all null, assign global mode 'bar'/'C'.
- Code: `COALESCE(pressure_unit, MODE() OVER (PARTITION BY batch_id), MODE() OVER (PARTITION BY reactor_id_norm))`

### 5.5 Validation of Recovery Method
- Method: Take rows where unit IS known, randomly set 20% to null, apply recovery, compute accuracy.
- Query: Use DuckDB `USING SAMPLE` or Python sklearn train_test_split.
- Result: Accuracy = [TODO]% (e.g., 98.7% recovered correctly). Precision per unit: [TODO]
- Conclusion: Method valid / not valid.
- Evidence: `docs/05_unit_recovery_validation.csv`

---

## 6. Outliers - Correct Order of Operations [BLOCKING ISSUE 5]

**Wrong order you used:** Compute max 1281.55 C / 1092.14 bar on mixed units.
**Correct order:** 1) Normalize labels 2) Convert all to C and bar_abs 3) Then find outliers.

After conversion to C and bar_abs (using recovery from Section 5):
- temp_c_norm: min=[TODO] C, max=[TODO] C, mean=[TODO], 825 rows < -273.15 C (impossible), [TODO] rows > 300 C (implausible for this process)
- pressure_bar_abs: min=[TODO], max=[TODO], 930 rows <0 bar (impossible), [TODO] rows > [TODO] bar
- agitator_rpm: min=[TODO], max=[TODO], 148 rows negative. Small negatives: distribution between -2 and 2: [TODO] - is it symmetric around 0 with cluster at -0.45? Evidence for zero-point drift? Large negatives: [TODO] -> glitch.
- feed_rate: max raw 59.04 but after unit conversion max = [TODO]

Planned cleaning: Mask impossible values to NULL, do NOT take absolute value (-691 C is not +691 C).
- temp < -273.15 or > [process max] -> NULL
- pressure < 0 or > [process max] -> NULL
- rpm < 0 -> NULL (or if drift proven, shift by +0.45 for values in [-2,0] only, with evidence)

Evidence: `docs/06_outliers_after_conversion.png`, `docs/06_negative_distribution.csv`

---

## 7. Missingness, Time, Reactor Distributions [BLOCKING ISSUE 6]

### 7.1 By Reactor (you did this, keep it)
- Consolidated R1-R8 each ~245k-258k rows.
- Missing rates uniform:
  temp_c: 4.29-4.63% (total 89,375)
  pressure_bar: 4.12-4.61% (86,910)
  agitator_rpm: 3.80-3.90% (77,260)
  feed_rate: 4.15-4.44% (86,418)
  ph: 4.05-4.73% (85,292)
  temp_unit & pressure_unit: ~20% uniformly
- Conclusion: Missingness independent of reactor hardware (no dead sensor). But NOT proven random. Confidence: High for reactor independence, Low for MCAR.
- Evidence: `docs/07_missing_by_reactor.csv`

### 7.2 By Shift (you did this, keep 4 separate)
- A,B,C,Night each ~500k rows, missing rates 4.16-4.61% uniform.
- Evidence: `docs/07_missing_by_shift.csv`

### 7.3 By Time [MISSING IN OLD FILE - Question 3]
- By month: `SELECT DATE_TRUNC('month', timestamp) as month, COUNT(*) as rows, COUNT(DISTINCT batch_id) as batches FROM t GROUP BY month ORDER BY month`
- Finding: [TODO: any shutdown months? volume drop?]
- By hour of day: [TODO: uniform or night lower?]
- Evidence: `docs/07_volume_by_month.png`, `docs/07_volume_by_hour.png`

### 7.4 Timestamp Integrity
- Ordering: `SELECT batch_id, timestamp, LAG(timestamp) OVER (PARTITION BY batch_id ORDER BY timestamp) as prev FROM t WHERE timestamp < prev` -> [TODO] out-of-order rows?
- Gaps: `SELECT batch_id, timestamp - prev as gap FROM ... WHERE gap > INTERVAL 2 MINUTE` -> [TODO] gaps >1 min?
- Overlap - Can one reactor run 2 batches at once? `SELECT reactor_id_norm, timestamp, COUNT(DISTINCT batch_id) as active FROM t GROUP BY reactor_id_norm, DATE_TRUNC('minute', timestamp) HAVING active>1`
- Finding: [TODO]
- Evidence: `docs/07_timestamp_gaps.csv`, `docs/07_reactor_overlap.csv`

### 7.5 Deeper Missingness (you missed this)
- Vs position in batch: `SELECT ROW_NUMBER() OVER (PARTITION BY batch_id ORDER BY timestamp) as pos, AVG(CASE WHEN temp_c IS NULL THEN 1 ELSE 0 END) as miss_rate FROM t GROUP BY pos ORDER BY pos`
- Finding: [TODO: higher at start/end?]
- Runs: Are nulls in streaks? `SELECT batch_id, COUNT(*) as run_length FROM (groups of consecutive nulls) GROUP BY batch_id`
- Finding: [TODO: e.g., 70% of nulls come in runs >10 min -> sensor offline, not random]
- Vs other columns: `SELECT * FROM t WHERE temp_c IS NULL AND pressure_bar IS NULL` correlation
- Evidence: `docs/07_missing_by_position.png`, `docs/07_missing_runs.csv`, `docs/07_missing_correlation.csv`

---

## 8. Duplicates and Grain

- Exact duplicates: 9,998 rows duplicated (19,996 rows with keep=False -> exact pairs). Removal: 2,009,978 -> 1,999,980.
- Grain: Telemetry = 1 row per minute per (batch_id, timestamp). Target = 1 yield_pct per batch_id (repeated across ~180 rows per batch, range 28.86% Batch 5 to 86.13% Batch 14).
- Implication: Feature engineering must aggregate 180 steps to batch-level (means, max, slope, time-above-threshold). CV must split by batch_id.
- Evidence: `docs/08_grain_check.csv`

---

## 9. Validation Design [Deliverable - 3 to 4 sentences required]

[REPLACE THIS WITH YOUR OWN 3-4 SENTENCES]

Example that passes:
We will split by batch_id using GroupKFold (k=5) so no batch appears in both train and val, preventing leakage from repeated yield values. Features will be aggregated from 180 time-steps to one vector per batch (11,110 samples). All unit conversion, outlier thresholds, and imputations will be learned only on train folds. Model performance will be measured by RMSE on yield_pct at batch level.

---

## 10. Unit Recovery Method Summary [Deliverable]

Method: [1 sentence summary of Section 5.4]
Validation: [1 sentence with accuracy from 5.5, e.g., Hid 20% known labels, recovered 98.7% correctly]
Limitation: [e.g., Batches with all nulls fallback to reactor mode, accuracy lower for those]

---

## 11. Anything I Could Not Explain [Deliverable]

- [TODO: e.g., Global 2-hour gap on 2023-04-12 02:00-04:00 for all reactors - no logs]
- [TODO: e.g., One lot LOT-XXX has only 2 variants, all others have 3]
- [TODO: e.g., After conversion, feed_rate still has 12 values > 60, exceeding physical max from spec sheet]
- [TODO: e.g., pH sensor missing 85,292 values but no pattern]

---

## 12. Confidence and Limitations

- High confidence: Reactor mapping 32->8, duplicates are exact pairs, missingness uniform across reactors.
- Medium confidence: Unit recovery [TODO]% accuracy, shift labels are crew not time.
- Low confidence / Not proven: Missingness is random (MCAR) - not tested vs yield yet. Zero-point drift for RPM - need symmetric distribution evidence.
- Limitations: [TODO]

---

## Appendix A - Evidence Files Checklist

You must have these in docs/ to pass:
- docs/01_batch_count.csv
- docs/01_lot_variant_check.csv
- docs/02_reactor_id_raw_counts.csv
- docs/02_shift_raw_counts.csv
- docs/03_yield_by_shift_batch.csv
- docs/03_yield_boxplot.png
- docs/04_shift_vs_hour.png
- docs/05_unit_constancy_per_batch.csv
- docs/05_pressure_unit_means.csv
- docs/05_unit_recovery_validation.csv
- docs/06_outliers_after_conversion.png
- docs/07_missing_by_reactor.csv
- docs/07_volume_by_month.png
- docs/07_timestamp_gaps.csv
- docs/07_missing_by_position.png
- docs/08_grain_check.csv

## Appendix B - Queries Used

Paste your DuckDB queries here for reproducibility.

