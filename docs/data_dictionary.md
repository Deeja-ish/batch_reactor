**1. batch_id**
*   Meaning: Unique identifier for a production run. 1 batch = ~180 time-steps.
*   Raw: INTEGER, 0 to 11110
*   Stats: 11,110 distinct using `SELECT DISTINCT(batch_id) FROM data_path GROUP BY batch_id ORDER BY batch_id ASC` i then check the min and max value 
*   Missing: 0%
*   Issue: None, but grain is important.
*   Plan: Keep as key. All modeling must GROUP BY batch_id.

**2. reactor_id**
*   Meaning: Physical reactor hardware. Should be R1-R8.
*   Raw: VARCHAR, 32 distinct raw values.
*   Example: `R1 (228k rows), r1 (8.4k), R-1 (8.2k), Reactor 1 (8.1k)` -> pattern repeats for R2-R8.
*   Issue: Manual entry typos, 4 spellings per reactor. Evidence: `32 = 8 * 4`.
*   Plan: Normalize to `R1-R8` via `UPPER(TRIM(REPLACE...))`.

**3. operator_shift**
*   Meaning: Assigned crew label. Dictionary looks like says 3 shifts: Morning/A, Afternoon/B, Night/C.
*   Raw: VARCHAR, 14 distinct raw values. `A, a, A␣, Shift A, B, b, Shift B, C, c, Shift C␣, Night, night, Night␣, N`
*   Stats: After light trim/lower, 4 groups at ~25% each (~500k rows). If Night=C, that crew would have ~50% of all work.
*   Issue: Label does NOT track clock time. Evidence: `SELECT timestamp::TIME, operator_shift FROM data_path WHERE operator_shift IN ('Night','N') LIMIT 10` shows 11:59, 13:05, 15:23.
*   Plan: **Keep 4 separate labels (A, B, C, Night) until proven otherwise.** Do NOT merge Night into C yet.

**4. catalyst_lot**
*   Meaning: Catalyst material lot, format should be `LOT-<number>`.
*   Raw: VARCHAR, 360 distinct raw strings. I have from Lot 0 - 119 which counts to 120
*   Issue: `360 / 3 = 120` Proves that almost every lot has 3 naming mistached on average but no certainty
*   Plan: Normalize via regex, produce mapping.

**5. pressure_bar + pressure_unit**
*   Meaning: Reactor pressure. Valid >0 bar absolute.
*   Raw: `pressure_bar` FLOAT, `pressure_unit` VARCHAR with 9 variants `[bar, barg, psi, psig, kPa...]` + ~20.0% nulls `402,966 nulls / 2,009,978 = 20.04%`.
*   Issue: Values are in mixed units, not just labels. 
*   Plan: 1. Determine if unit is constant within batch: From the data every batch seems to have on average 8 distinct pressuer unit.

**6. temp_c + temp_unit**
*   Same pattern. 10 variants `[C, degC, F, K...]` + ~20.0% nulls `402,061 nulls`. 825 rows < -273.15 C. Max you quoted 1281 is on mixed units, meaningless until normalized to C. 2. On average every batch seeme to have 9 distinct temperature units but some are more and some are less.

**7. agitator_rpm**
*   Meaning: Agitator speed, must be >=0.
*   Raw: FLOAT, 77,260 nulls (3.84%). 148 rows negative.
*   Issue: Small negatives around -0.45 could be zero-point drift, large negatives (-200) cannot. Check distribution: `SELECT * FROM t WHERE agitator_rpm BETWEEN -2 AND 2 ORDER BY agitator_rpm`. there is no drift because i have only aroud 5 rows that are between -2 and 2.

**8. timestamp**
*   Meaning: Time recorded for every batch run time difference is 1 min .
*   Raw: DateTime column
*   Stats: The data started from 2022 january first and dated up to febuary 24.
*   Missing: 0%
*   Issue: The time stamp eventhough when compared with the batch_id seem to align with every batch but there is a mis-alignment with the operator shift.
*   Plan: Keep for now but may consider removing if proven to provide leak when training model.

**9. feed_rate**
*   Meaning: The amount of starting material feed into the reactor.
*   Raw: Float
*   Missing: 86418 nulls, (4.3%) No-Negetive values
*   Issue: None. After grouping by batch_id and taking the average of each batch the feed rate is between 49 - 52 for almost all batches

**10. feed_purity**
*   Meaning: The percentage purity of the starting material feed that is fed into the reactor.
*   Raw: Float column
*   Missing: None, No negetive value as well.
*   Issue: None. After grouping by batch_id and taking the average of each batch the feed purity ranges between 94-100 for each batch and also there are some inconsistences in the feed purity values some are in decimals and some are not in decimals e.g 0.98, 0.94, 98.78, 99.00
*   Plan: To turn the into similar format

**11. ph**
*   Meaning: pH reading value ranging from 0-14 so the values cannot be < 0 or > 14
*   Raw: Float Values.
*   Missing: 85292 nulls (4.24%) no negetive values 
*   Issue: None.  All ph seem from the data ranges from 6-7 and stays within this range through out

**11. ambient_humidity**
*   Meaning: Tha amount of water or vapour present in the surroung air per every minute of the process for every batch.
*   Raw: Float values
*   Missing: No missing value
*   Issue: None. The values in this colum ranges form 20-90.