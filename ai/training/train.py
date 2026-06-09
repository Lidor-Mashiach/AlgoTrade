"""Full training entry point: build dataset -> fit -> validate -> plot -> save artifact."""
from __future__ import annotations
from ..datasets.builder import build_dataset
from ..models.registry import get_model, artifact_path


def train(index: str, horizon: str, cfg: dict) -> None:
    # X_tr, y_tr, X_val, y_val, X_te, y_te = build_dataset(index, horizon, cfg)
    # model = get_model(index, horizon); model.fit(X_tr, y_tr)
    # ... validate, plot learning curves, evaluate on test ...
    # model.save(artifact_path(index, horizon))
    raise NotImplementedError
