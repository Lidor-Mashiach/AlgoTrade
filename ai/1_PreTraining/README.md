# 🪒 PreTraining

This folder turns the backend's raw per-ticker tables into the engineered, split datasets
that training consumes. It is the only place that touches raw data and the only place that
builds the label.

Run it with `run_pretraining.py`, or run any single stage directly. Each stage reads its
input from the intermediate data store and writes its output back, so the same table flows
from one stage to the next.

---

## 🧱 Stages

| Order | Script | What it does |
| --- | --- | --- |
| 1 | `Data-Extraction/extract_dataset.py` | Pulls each ticker, pools them with a ticker column, and splits the wide table into three per-horizon raw datasets by column suffix |
| 2 | `Feature-Eng/check_missing.py` | Reports missing values per horizon and drops rows with no anchor close |
| 3 | `Feature-Eng/build_features.py` | Builds the relative features and the label, then drops raw price columns |
| 4 | `Feature-Eng/run_eda.py` | Saves a correlation heatmap and a non-linear association report |
| 5 | `Feature-Eng/split_dataset.py` | Produces the group-aware, per-ticker proportional train and test splits |

---

## 🔌 Backend boundary

The single touch point with the data layer is `load_raw_ticker_table` in the extraction
script. It is a thin adapter that returns one wide raw table per ticker. No backend logic
lives in this folder.

- Until the backend is wired, the adapter reads a template table per ticker and raises a
  clear error if one is missing.
- The expected raw schema is described in `../FEATURES.md` and the main `../README.md`.

---

## 🎯 The label

The label is built in `build_features.py` and is the only computation allowed to look
forward.

- **Daily** is the next day's percent move from the current daily close.
- **Weekly** and **monthly** are the percent move from the row's anchor to the in-progress
  candle's closing value.
- Rows whose candle has not closed are dropped, because their label is not realized.

No feature uses any future information.

---

## ✂️ Splitting philosophy

The split is built to avoid leakage and to keep the test set representative.

- **Group first, window second.** The split is decided at the candle level. For weekly and
  monthly, all intra-candle rows of one candle share a group, so a single candle never
  straddles train and test. The intra-candle rows follow their group rather than being split
  independently.
- **Per ticker and time ordered.** Each index holds out its most recent share of candles, so
  every index is represented in proportion and the test period is the most recent. This also
  removes any look-ahead from the holdout.
- **Group identifier kept.** A `group_id` column is carried into both parts so the training
  stage can run GroupKFold without a candle leaking across folds.

---

## 📤 Outputs

Into the intermediate data store:

- `data_store/raw/<horizon>` after extraction.
- `data_store/features/<horizon>` after feature engineering.
- `data_store/splits/<horizon>/train` and `.../test` after splitting.

Into `results/` (latest run only, categorized):

- `results/tables/missing_values/` the missing-value reports.
- `results/tables/feature_engineering/` the final model feature list per horizon.
- `results/plots/eda/<horizon>/` the correlation heatmap and the mutual-information chart.
- `results/tables/eda/<horizon>/` the signed correlation matrix and the association table.
- `results/tables/split/` the split size summary.
