"""Model interface. Every model must support full fit, incremental update, predict, save/load."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseModel(ABC):
    @abstractmethod
    def fit(self, X, y) -> None:
        """Full training run."""

    @abstractmethod
    def partial_fit(self, X, y) -> None:
        """Incremental update on newly-closed candles (no train-from-scratch)."""

    @abstractmethod
    def predict(self, features: dict) -> dict:
        """Return {low, high, confidence} — low/high are % moves of the next close."""

    @abstractmethod
    def save(self, path: str) -> None: ...
    @abstractmethod
    def load(self, path: str) -> "BaseModel": ...
