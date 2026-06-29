"""
Evaluation metrics for quantile (interval) forecasts.

This module is the single place that defines how we judge the models. It is pure
numpy with no plotting and no file writing, so it can be imported by the test stage,
the inference build, or a notebook without side effects.

The model outputs three numbers per row (Q10, Q50, Q90), all in percentage points.
The label y is the realized percentage move of the candle. Read Evaluation/README.md
for the plain-language meaning of each metric and why it was chosen.
"""

from __future__ import annotations

import numpy as np

# Predicted recommendation classes, derived from the band sign.
PRED_CLASSES = ["Short", "Stay-out", "Long"]
# Realized outcome classes, derived from where the move landed relative to the band.
ACTUAL_CLASSES = ["Below band", "Within band", "Above band"]


def coverage(y: np.ndarray, q_low: np.ndarray, q_high: np.ndarray) -> float:
    """
    Fraction of realized moves that landed inside the predicted band [Q10, Q90].

    This is the primary correctness metric: did the candle actually close inside the
    range the model promised? A band built for 80% coverage should sit near 0.80.
    """
    y, q_low, q_high = np.asarray(y), np.asarray(q_low), np.asarray(q_high)
    inside = (y >= q_low) & (y <= q_high)
    return float(np.mean(inside))


def mean_band_width(q_low: np.ndarray, q_high: np.ndarray) -> float:
    """
    Average width of the band (Q90 minus Q10), in percentage points.

    Coverage on its own can be gamed by a huge band that always contains the move.
    Width is the cost side of that trade, so coverage and width are always read together.
    """
    q_low, q_high = np.asarray(q_low), np.asarray(q_high)
    return float(np.mean(q_high - q_low))


def pinball_loss(y: np.ndarray, pred: np.ndarray, alpha: float) -> float:
    """
    Pinball (quantile) loss for a single quantile. This is the loss the model minimizes
    and the proper scoring rule for a quantile forecast: it rewards a quantile that sits
    in the right place, penalizing under- and over-prediction asymmetrically by alpha.
    Lower is better.
    """
    y, pred = np.asarray(y), np.asarray(pred)
    error = y - pred
    loss = np.where(error >= 0, alpha * error, (alpha - 1.0) * error)
    return float(np.mean(loss))


def q50_errors(y: np.ndarray, q_mid: np.ndarray) -> dict[str, float]:
    """
    Point-accuracy of the central forecast (Q50): MAE and RMSE in percentage points.
    These answer how close the median prediction is, separate from the band.
    """
    y, q_mid = np.asarray(y), np.asarray(q_mid)
    err = y - q_mid
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    return {"mae": mae, "rmse": rmse}


def directional_accuracy(y: np.ndarray, q_mid: np.ndarray) -> float:
    """
    Share of rows where the sign of the central forecast matches the sign of the
    realized move. A simple "did we call up vs down correctly" score for Q50.
    """
    y, q_mid = np.asarray(y), np.asarray(q_mid)
    return float(np.mean(np.sign(y) == np.sign(q_mid)))


def interval_score(y: np.ndarray, q_low: np.ndarray, q_high: np.ndarray,
                   nominal_coverage: float) -> float:
    """
    Winkler interval score for a central prediction interval. It combines width and a
    penalty for every miss into one number, so a narrow band that still covers well
    scores best. Lower is better. This is the principled single-number summary of an
    interval forecast.
    """
    y, q_low, q_high = np.asarray(y), np.asarray(q_low), np.asarray(q_high)
    alpha = 1.0 - nominal_coverage          # total tail probability, for example 0.20
    width = q_high - q_low
    below = (2.0 / alpha) * (q_low - y) * (y < q_low)
    above = (2.0 / alpha) * (y - q_high) * (y > q_high)
    return float(np.mean(width + below + above))


def predicted_recommendation(q_low: np.ndarray, q_high: np.ndarray) -> np.ndarray:
    """
    Map each band to a recommendation, mirroring the rule the backend and CLI use.
    Fully positive band -> Long. Fully negative band -> Short. Straddles zero -> Stay-out.
    Returned as integer codes: 0 Short, 1 Stay-out, 2 Long (indexes into PRED_CLASSES).
    """
    q_low, q_high = np.asarray(q_low), np.asarray(q_high)
    codes = np.full(q_low.shape, 1, dtype=int)   # default Stay-out
    codes[q_low > 0] = 2                          # fully positive -> Long
    codes[q_high < 0] = 0                         # fully negative -> Short
    return codes


def actual_band_class(y: np.ndarray, q_low: np.ndarray, q_high: np.ndarray) -> np.ndarray:
    """
    Classify each realized move relative to the band the model produced.
    Below the band, inside the band, or above the band. Integer codes 0 / 1 / 2
    (indexes into ACTUAL_CLASSES). Both axes of the confusion matrix are defined by
    the band, which keeps the matrix internally consistent with coverage.
    """
    y, q_low, q_high = np.asarray(y), np.asarray(q_low), np.asarray(q_high)
    codes = np.full(y.shape, 1, dtype=int)        # default within band
    codes[y < q_low] = 0                          # broke below
    codes[y > q_high] = 2                          # broke above
    return codes


def directional_confusion_matrix(y: np.ndarray, q_low: np.ndarray,
                                 q_high: np.ndarray) -> np.ndarray:
    """
    Build the 3x3 confusion matrix of predicted recommendation against realized outcome.

    Rows are predicted classes (PRED_CLASSES), columns are actual classes
    (ACTUAL_CLASSES). The diagonal is the set of calibrated, directionally consistent
    hits:
        (Short, Below band)  the model leaned short and the move broke down
        (Stay-out, Within band)  the model was cautious and the move stayed in range
        (Long, Above band)  the model leaned long and the move broke up
    Returns the raw count matrix.
    """
    pred = predicted_recommendation(q_low, q_high)
    actual = actual_band_class(y, q_low, q_high)
    matrix = np.zeros((3, 3), dtype=int)
    for p, a in zip(pred, actual):
        matrix[p, a] += 1
    return matrix


def confusion_accuracy(matrix: np.ndarray) -> float:
    """Diagonal sum over total: the share of calibrated, direction-consistent decisions."""
    total = matrix.sum()
    return float(np.trace(matrix) / total) if total else 0.0


def evaluate_all(y: np.ndarray, q_low: np.ndarray, q_mid: np.ndarray,
                 q_high: np.ndarray, nominal_coverage: float,
                 alphas: dict[str, float]) -> dict[str, float]:
    """
    Run every scalar metric at once and return a flat dictionary. Plotting (the band
    chart and the confusion-matrix image) is handled by the test stage, not here.
    """
    errors = q50_errors(y, q_mid)
    return {
        "n_samples": int(len(y)),
        "coverage": coverage(y, q_low, q_high),
        "nominal_coverage": float(nominal_coverage),
        "mean_band_width": mean_band_width(q_low, q_high),
        "interval_score": interval_score(y, q_low, q_high, nominal_coverage),
        "pinball_q10": pinball_loss(y, q_low, alphas["q10"]),
        "pinball_q50": pinball_loss(y, q_mid, alphas["q50"]),
        "pinball_q90": pinball_loss(y, q_high, alphas["q90"]),
        "q50_mae": errors["mae"],
        "q50_rmse": errors["rmse"],
        "directional_accuracy": directional_accuracy(y, q_mid),
        "confusion_accuracy": confusion_accuracy(
            directional_confusion_matrix(y, q_low, q_high)
        ),
    }
