# 📏 Evaluation

This folder defines how we judge the models. The models do not predict a single number,
they predict a **band** (Q10 to Q90) with a median (Q50). So the evaluation is built for
interval forecasts, not for ordinary point forecasts.

All metrics live in `metrics.py` as pure functions. The test stage in `../Train` calls
them, computes the figures, and writes the results.

---

## 🎯 What we are really asking

The core question is simple. For each candle the model produced a range. **Did the candle
actually close inside that range?** That question is answered by coverage, and it is the
metric everything else is built around. The other metrics exist to stop coverage from being
gamed and to describe the quality of the decision the band implies.

A band also implies a recommendation. A band fully above zero leans **Long**, a band fully
below zero leans **Short**, and a band that straddles zero is **Stay-out**. The confusion
matrix scores that decision.

---

## 🧮 Metrics at a glance

| Metric | Plain question it answers | Better when |
| --- | --- | --- |
| **Coverage** | How often did the move land inside the band | Close to the target (0.80) |
| **Mean band width** | How wide is the band on average | Lower, given good coverage |
| **Interval score** | One number for a sharp band that still covers | Lower |
| **Pinball loss (per quantile)** | Is each quantile in the right place | Lower |
| **Q50 MAE and RMSE** | How close is the central forecast | Lower |
| **Directional accuracy** | Did the median call up versus down correctly | Higher |
| **Confusion matrix accuracy** | Was the recommendation calibrated and directionally right | Higher |

---

## ✅ Coverage (primary)

- **What it means.** The share of candles whose realized move fell inside the predicted
  band. A band designed for eighty percent coverage should land near 0.80 on the test set.
- **Why we chose it.** It is the direct, honest answer to the question the product asks. The
  band is a promise about where the close will be, and coverage measures how often that
  promise held.
- **Advantage here.** A trading recommendation built on an interval is only trustworthy if
  the interval is calibrated. Coverage is the one number that tells us whether to trust the
  band at all. Everything else is secondary to it.

---

## 📐 Mean band width

- **What it means.** The average distance between Q90 and Q10, in percentage points.
- **Why we chose it.** Coverage on its own can be cheated. A band from minus fifty to plus
  fifty percent would contain almost every move and score perfect coverage, while saying
  nothing useful. Width is the cost of that trick, so coverage and width are always read as
  a pair.
- **Advantage here.** It keeps the models honest. A good model reaches the coverage target
  with the narrowest band it can, which is exactly the sharp and reliable range a trader
  wants.

---

## 🪟 Interval score (Winkler)

- **What it means.** A single number that rewards a narrow band and adds a penalty every
  time the move falls outside it. Lower is better.
- **Why we chose it.** It folds the coverage versus width trade-off into one value, so two
  models can be ranked directly instead of by eyeballing two separate numbers.
- **Advantage here.** It is the standard, principled score for prediction intervals. It lets
  us compare horizons and configurations with one consistent objective that matches what we
  care about, a band that is both tight and reliable.

---

## 🎿 Pinball loss (per quantile)

- **What it means.** The loss each quantile is trained to minimize. It penalizes a quantile
  asymmetrically, so the Q10 booster is pushed to sit near the true tenth percentile and the
  Q90 booster near the true ninetieth.
- **Why we chose it.** It is the proper scoring rule for a quantile, which means the best
  possible score is reached only when the quantile is in its correct place. It is also the
  exact objective the boosters optimize, so test pinball loss measures the thing the model
  was built to do.
- **Advantage here.** It evaluates each band edge on its own. Coverage tells us about the
  band as a whole, while pinball loss tells us whether a specific edge is too wide or too
  tight, which is useful when one tail is well behaved and the other is not.

---

## 🎯 Q50 accuracy (MAE and RMSE)

- **What it means.** The error of the central forecast. MAE is the average absolute error
  and RMSE punishes large misses more. Both are in percentage points.
- **Why we chose it.** The band describes uncertainty, but the median is the single best
  guess of the move. These two numbers describe how good that guess is, separately from the
  band.
- **Advantage here.** RMSE surfaces the occasional large miss that a trader cares about,
  while MAE gives the typical error in plain units. Together they describe the central
  forecast without the band getting in the way.

---

## 🧭 Directional accuracy

- **What it means.** The share of candles where the sign of the median matches the sign of
  the realized move, a plain up versus down hit rate.
- **Why we chose it.** A recommendation is ultimately directional, so a simple, readable
  measure of how often the central call points the right way is valuable on its own.
- **Advantage here.** It is easy to communicate and is independent of the band. It answers
  the blunt question, when the model leaned a direction, was it right.

---

## 🔢 Directional confusion matrix

This is the decision-quality view. Both axes are defined by the band, which keeps the matrix
consistent with coverage.

- **Predicted recommendation (rows).**
  - **Short** when the whole band is below zero.
  - **Stay-out** when the band straddles zero.
  - **Long** when the whole band is above zero.
- **Realized outcome (columns).**
  - **Below band** when the move fell under Q10.
  - **Within band** when the move landed inside the band.
  - **Above band** when the move broke above Q90.

The diagonal is the set of calibrated, directionally consistent outcomes.

| pred \ actual | Below band | Within band | Above band |
| --- | --- | --- | --- |
| **Short** | hit (leaned short, broke down) | cautious miss | wrong direction |
| **Stay-out** | broke low | hit (cautious and contained) | broke high |
| **Long** | wrong direction | cautious miss | hit (leaned long, broke up) |

- **What it means.** It shows not just how often the decision was right, but how it was
  wrong. A Short that ended in an Above band break is a serious error, while a Long whose
  move stayed inside the band is only a mild one.
- **Why we chose it.** A single accuracy number hides the kind of mistake. The confusion
  matrix separates a costly wrong-direction call from a harmless cautious one, which matters
  for a trading decision.
- **Advantage here.** It ties the recommendation back to the same band that coverage scores,
  so the calibration view and the decision view stay consistent. The `(Stay-out, Within
  band)` cell directly rewards justified caution, which a plain accuracy score would punish.

---

## 🔗 How to read them together

1. Start with **coverage**. If it is far from the target, the band is not calibrated and the
   rest is secondary.
2. Read coverage next to **mean band width**, or use the **interval score** to combine them.
3. Use **pinball loss** to see which band edge is responsible when coverage drifts.
4. Use **Q50 MAE and RMSE** and **directional accuracy** to judge the central forecast.
5. Use the **confusion matrix** to judge the recommendation and the kind of errors it makes.

---

## 🗂️ Where the outputs go

The test stage writes, per horizon, into the categorized results tree:

- `results/metrics/test_<horizon>/metrics.json` with every scalar metric and the confusion
  matrix counts.
- `results/reports/test_<horizon>/report.md`, a short readable summary.
- `results/plots/test_<horizon>/interval.png`, the predicted band against the realized moves.
- `results/plots/test_<horizon>/confusion_matrix.png`, the directional confusion matrix.
- `results/plots/test_<horizon>/q50_residuals.png`, the central-forecast error distribution.
- `results/metrics/test_<horizon>/<quantile>/pinball.txt`, that quantile's pinball loss.

Only the latest run is kept.
