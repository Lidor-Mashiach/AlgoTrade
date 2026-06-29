# 🚀 Inference_models

This folder builds the models that ship and provides the runtime entry point the backend and
CLI call. It takes the splits produced by PreTraining, refits on all of the data, and saves
the deployable boosters with their metadata.

Run it with `run_final_training.py`, which builds the models and then runs a smoke test.

---

## 🧱 What it produces

| File | Role |
| --- | --- |
| `build_final_models.py` | Refits the three quantile boosters per horizon on all data and saves them with metadata |
| `predictor.py` | The runtime entry point, returns a band and a confidence from a feature row |
| `verify_inference.py` | A smoke test that loads the models and runs a dummy prediction |

---

## 🔁 Build on all data

The development models in `../2_Train` are trained on the train split so they can be judged on
an untouched test split. The deployable models are different. Once the evaluation is trusted,
there is no reason to hold data back, so this stage unifies the train and test splits and
refits on the full dataset. It reuses the number of boosting rounds chosen during
development cross-validation.

This is a **full retrain**. There is no continued training. When new data arrives, this stage
runs again from scratch. The metadata records `last_trained_through` per horizon so it is
always clear how current a model is.

---

## 🔮 The prediction contract

`predictor.py` exposes one stable function:

```python
predict(ticker: str, horizon: str, features: dict) -> {
    "low": Q10, "mid": Q50, "high": Q90, "confidence": float
}
```

- `low` and `high` are the band edges in percentage points and `mid` is the median.
- `confidence` is a value between zero and one that rises as the band tightens.
- The band edges are sorted, so `low` never exceeds `high` even on the rare row where the
  quantiles cross.
- Unknown feature keys are ignored and missing model features are left as missing, which
  LightGBM handles natively.

The recommendation mapping, Long versus Short versus Stay-out, is applied downstream by the
backend or CLI. The predictor returns the band and the confidence only.

---

## 📦 Models and caching

- Boosters are saved to `Inference_models/<horizon>/<quantile>.txt` with a `metadata.json`
  per horizon. The `Inference_models/` folder is tracked in git so the backend and CLI can
  load the production models without retraining.
- The predictor loads a horizon's models on first use and caches them, so the first call pays
  the load cost and later calls are fast.
- The metadata stores the feature order, so the predictor always builds the feature row in
  the exact order the model was trained on.
