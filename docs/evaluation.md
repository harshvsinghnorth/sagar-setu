# Sagar Setu — verdict evaluation

*Generated 2026-09-22T09:48 UTC by `scripts/eval_report.py`. Raw numbers: `data/eval/backtest.json`.*

## What is being measured, honestly

The question a reviewer asks is: *when the system says "do not go out tomorrow morning", how often is it right?* Sagar Setu does not forecast the sea itself — it applies published small-craft thresholds to government and open forecasts. So the verdict can be wrong for two reasons: the forecast was wrong, or the threshold was. This evaluation measures both together, the way the fisherman experiences them.

**Prediction:** the verdict computed from the forecast available the evening before (the model run issued 1, 2 or 3 days ahead of the morning in question).  
**Truth:** the verdict computed from the same wave/weather model's *final analysis* for that morning (lead 0–23 h). This is the model's best estimate of what happened — **not a buoy measurement**. No INCOIS/NIOT buoy feed is publicly accessible to us; if one is obtained the same harness runs against it unchanged. Forecast-versus-analysis agreement is expected to be somewhat better than forecast-versus-buoy, so treat these as an upper bound on skill.

**Sample:** 92 mornings (2026-06-22 → 2026-09-21) × 5 harbours = 460 harbour-mornings per lead. The period covers the peak of the south-west monsoon, so rough mornings are well represented.  
**Window:** 05:00–12:00 IST (00–06 UTC), worst-of per parameter. **Vessel class:** traditional (< 12 m). **Parameters:** wave height, wave period (steepness), wind, gusts; visibility held neutral; lightning/cyclone absent in both.

Two errors matter differently. A **miss** (we said go, it was rough) is the dangerous one. A **false alarm** (we said don't go, it was fine) is the wasted day. They are reported separately, using the standard warning-verification table:

- **Hit rate (POD)** = hits / (hits + misses) — of the rough mornings, how many were warned.
- **False-alarm ratio (FAR)** = false alarms / (hits + false alarms) — of the warnings, how many wasted a day.
- **CSI** = hits / (hits + misses + false alarms). **Accuracy** = (hits + correct negatives) / all.

## Results — all five harbours pooled

### Event: DO NOT SAIL (the do-not-sail band on any parameter)

| Forecast lead | n | rough mornings | hits | misses | false alarms | hit rate | false-alarm ratio | CSI | accuracy |
|---|---|---|---|---|---|---|---|---|---|
| 1 day ahead | 460 | 7.2% | 31 | 2 | 1 | **93.9%** | **3.1%** | 91.2% | 99.3% |
| 2 day ahead | 460 | 7.2% | 32 | 1 | 7 | **97.0%** | **17.9%** | 80.0% | 98.3% |
| 3 day ahead | 460 | 7.2% | 30 | 3 | 13 | **90.9%** | **30.2%** | 65.2% | 96.5% |

### Event: CAUTION or worse (anything other than a clean GO)

| Forecast lead | n | such mornings | hits | misses | false alarms | hit rate | false-alarm ratio | CSI | accuracy |
|---|---|---|---|---|---|---|---|---|---|
| 1 day ahead | 460 | 47.0% | 196 | 20 | 7 | **90.7%** | **3.4%** | 87.9% | 94.1% |
| 2 day ahead | 460 | 47.0% | 187 | 29 | 8 | **86.6%** | **4.1%** | 83.5% | 92.0% |
| 3 day ahead | 460 | 47.0% | 184 | 32 | 21 | **85.2%** | **10.2%** | 77.6% | 88.5% |

### Three-way agreement and wave-height error

| Forecast lead | GO/CAUTION/NO-GO agreement | wave-height MAE | RMSE | bias |
|---|---|---|---|---|
| 1 day ahead | **93.5%** | 0.056 m | 0.094 m | -0.021 m |
| 2 day ahead | **90.2%** | 0.101 m | 0.146 m | +0.002 m |
| 3 day ahead | **85.0%** | 0.121 m | 0.174 m | +0.018 m |

### Confusion matrix, 1 day ahead (rows = what the morning brought, columns = what was said)

| | said GO | said CAUTION | said DO NOT SAIL |
|---|---|---|---|
| was GO | 237 | 7 | 0 |
| was CAUTION | 20 | 162 | 1 |
| was DO NOT SAIL | 0 | 2 | 31 |

## Results per harbour, 1 day ahead

| Harbour | days | rough (NO-GO) mornings | NO-GO hit rate | NO-GO false-alarm ratio | CAUTION+ base rate | CAUTION+ hit rate | CAUTION+ FAR | 3-way agreement | Hs MAE |
|---|---|---|---|---|---|---|---|---|---|
| Kochi | 92 | 1 | 100.0% | 0.0% | 42.4% | 97.4% | 5.0% | 96.7% | 0.033 m |
| Veraval | 92 | 27 | 96.3% | 0.0% | 87.0% | 97.5% | 0.0% | 96.7% | 0.088 m |
| Chennai | 92 | 0 | — | — | 4.3% | 0.0% | — | 95.7% | 0.036 m |
| Paradip | 92 | 5 | 80.0% | 20.0% | 68.5% | 98.4% | 1.6% | 95.7% | 0.058 m |
| Port Blair | 92 | 0 | — | — | 32.6% | 60.0% | 18.2% | 82.6% | 0.065 m |

A dash means the event never occurred at that harbour in the period (Chennai and Port Blair had no do-not-sail mornings in the south-west monsoon — the Bay of Bengal's rough season is October–December). Veraval, on the Gujarat coast, is the stress test: a do-not-sail morning roughly one day in three.

## Prospective log (predictions made before the fact)

_Not started. `scripts/daily_log.py --log` each evening and `--verify` each afternoon build it._

## How to read this, and what it does not say

- The day-ahead do-not-sail verdict warned rough mornings with a high hit rate and a low false-alarm ratio; the misses were graded CAUTION, never GO. That is the behaviour the worst-of rule is designed to produce.
- Skill falls with lead time, mostly through false alarms — a three-day-ahead warning wastes more days. The interface should therefore present the day-ahead verdict as the decision and longer leads as outlook.
- These numbers are forecast-versus-analysis. Against buoy observations they would be lower, and the gap is the forecast model's own error near the coast, which is published by ECMWF and Copernicus for their wave products.
- The thresholds are still the provisional starting values. If INCOIS's published criteria differ, the base rates change and this report is regenerated with one command.
- Lightning and cyclone parameters are absent from both prediction and truth (no IMD feed), so this evaluation says nothing about them.

Re-run with `uv run python scripts/eval_report.py`.