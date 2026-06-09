# 🧠 AI Module

> Owns the learning side: **datasets → model(s) → training → incremental update → inference**.
> Consumes the exact feature set produced by the backend and returns, per `(index, horizon)`,
> a forecast **range** `[low%, high%]` with a **confidence** score.
>
> 👤 **Owner:** You (me)

---

## 🧭 Contents

1. [What this module guarantees](#-what-this-module-guarantees)
2. [Folder structure](#-folder-structure)
3. [Input features](#-input-features)
4. [Prediction targets](#-prediction-targets)
5. [Open modeling questions](#-open-modeling-questions-to-decide-together)
6. [Incremental update strategy](#-incremental-update-strategy)
7. [Inference contract](#-inference-contract)

---

## ✅ What this module guarantees

- A stable `predict(index, horizon, features) → {low, high, confidence}` contract for the backend.
- Models persisted as **artifacts** in `ai/artifacts/` (git-ignored), versioned by
  `(index, horizon)` so the rest of the system never retrains on demand.
- An **incremental update** path so new candles are absorbed **without** training from scratch.

---

## 📂 Folder structure

```
ai/
├── README.md
├── datasets/
│   └── builder.py        ← build train/val/test from the feature table
├── models/
│   ├── base_model.py     ← interface: fit / partial_fit / predict / save / load
│   └── registry.py       ← resolve the right model for (index, horizon)
├── training/
│   ├── train.py          ← full training run + validation + plots
│   └── incremental.py    ← warm-start / partial_fit on missed candles
├── inference/
│   └── predictor.py      ← returns (low, high, confidence)
└── artifacts/            ← saved models (git-ignored)
```

---

## 📥 Input features

The model consumes **exactly** the features defined in
**[`../backend/FEATURES.md`](../backend/FEATURES.md)** — there is no second list.
If the catalog changes, retraining/feature-alignment is required.

Quick reminder of the groups: price & returns, SMA, EMA, volume, range (Low/High),
Bollinger Bands, RSI, and VIX (feature only) — each across daily / weekly / monthly horizons.

---

## 🎯 Prediction targets

Per `(index, horizon)`, predict the **% move of the next candle's close** vs. the last closed candle:

| Output | Meaning |
|--------|---------|
| `pred_low` | lower bound of expected % move |
| `pred_high` | upper bound of expected % move |
| `confidence` | confidence in the range (0–1) |

Recommendation mapping (done in backend/CLI, not here): all-positive → **Long**,
all-negative → **Short**, straddles 0 → **Stay out**.

---

## ❓ Open modeling questions (to decide together)

These are intentionally **not** locked yet — they're the core of the next conversation.

### 1. One model or many?
- **Per `(index × horizon)`** → e.g. `SPY-daily`, `SPY-weekly`, … (≈ 6 indices × 3 = 18 models).
  - ➕ each specializes; cleaner targets. ➖ more artifacts, less data per model.
- **Per horizon, index as a feature** → 3 models.
  - ➕ shares cross-index patterns, more data. ➖ assumes indices behave comparably.
- **One global model** with `(index, horizon)` as features → 1 model.
- **Default assumption in this template:** per `(index × horizon)` via `models/registry.py`,
  but the registry is built so we can collapse it later.

### 2. How far back to collect data?
TBD — depends on the source's history and on how stationary we believe markets are.
Decide before the first full training run.

### 3. How to produce a *range*, not a point?
- mean prediction **± k·σ** (σ from residuals / recent volatility), or
- **quantile regression** (predict the 10th/90th percentile directly).

---

## 🔁 Incremental update strategy

The system runs locally and intermittently. We must avoid full retrains on every new candle.

| Option | Idea | Notes |
|--------|------|-------|
| **Warm-start / `partial_fit`** | continue from saved weights on the missed candles | works for SGD-based / many sklearn & NN models |
| **Rolling window** | keep only the last *N* periods; drop the oldest | bounds disk usage, fights data-bloat |
| **Periodic full retrain** | full retrain on a schedule (e.g. monthly) | safety net against drift |

**Do we need to keep all original training data?**
Not necessarily — a **rolling window** (or storing learned state + a recent window) avoids the
storage blow-up from accumulating every historical record. The backend's
"missed N candles" signal tells us exactly how much to feed the incremental step.

> This is the part you flagged as yours to design — the template just leaves clean seams
> (`base_model.partial_fit`, `training/incremental.py`) so any of the above plugs in.

---

## 🔌 Inference contract

```python
# inference/predictor.py
def predict(index: str, horizon: str, features: dict) -> dict:
    """
    Returns:
        {"low": float, "high": float, "confidence": float}  # low/high are % moves
    """
```

The backend calls this; the CLI renders the result. Keep this signature stable.
