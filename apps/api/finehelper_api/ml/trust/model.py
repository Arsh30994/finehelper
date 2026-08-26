"""Train / load thin-file trust model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from finehelper_api.ml.trust import FEATURE_NAMES
from finehelper_api.ml.trust.features import eligibility_band, extract_features, factor_breakdown
from finehelper_api.ml.trust.synthetic import generate_signal_batch

MODEL_VERSION = "v1"


def _label_from_quality(quality: str, noise: float) -> float:
    base = {"good": 78.0, "mixed": 58.0, "thin": 32.0}[quality]
    return float(np.clip(base + noise, 5, 98))


def build_training_matrix(n: int = 600, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows: list[list[float]] = []
    labels: list[float] = []
    qualities = ["good", "mixed", "thin"]
    occupations = ["kirana", "gig", "vendor", "farmer"]
    for i in range(n):
        q = qualities[i % 3]
        batch = generate_signal_batch(
            seed=int(rng.integers(0, 1_000_000)),
            occupation=occupations[i % len(occupations)],
            quality=q,
        )
        feats = extract_features(batch)
        rows.append([feats[k] for k in FEATURE_NAMES])
        labels.append(_label_from_quality(q, float(rng.normal(0, 6))))
    return np.asarray(rows, dtype=float), np.asarray(labels, dtype=float)


def train_and_save(path: str | Path, n: int = 600) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    X, y = build_training_matrix(n=n)
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=120,
                    max_depth=10,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipe.fit(X, y)
    joblib.dump({"pipeline": pipe, "features": FEATURE_NAMES, "version": MODEL_VERSION}, path)
    return path


class TrustModel:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._bundle: dict[str, Any] | None = None

    def load(self) -> None:
        if not self.path or not self.path.exists():
            # Train a small in-memory model for first boot
            X, y = build_training_matrix(n=240, seed=7)
            pipe = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", RandomForestRegressor(n_estimators=80, max_depth=8, random_state=7, n_jobs=-1)),
                ]
            )
            pipe.fit(X, y)
            self._bundle = {"pipeline": pipe, "features": FEATURE_NAMES, "version": MODEL_VERSION}
            return
        self._bundle = joblib.load(self.path)

    @property
    def ready(self) -> bool:
        return self._bundle is not None

    def predict(self, batch: dict[str, Any]) -> dict[str, Any]:
        if not self._bundle:
            self.load()
        assert self._bundle is not None
        feats = extract_features(batch)
        names: list[str] = list(self._bundle["features"])
        x = np.asarray([[feats.get(k, 0.0) for k in names]], dtype=float)
        raw = float(self._bundle["pipeline"].predict(x)[0])
        score = int(round(max(0.0, min(100.0, raw))))
        factors = factor_breakdown(feats)
        lo, hi = eligibility_band(score)
        return {
            "score": score,
            "factors": factors,
            "features": feats,
            "eligibility_min": lo,
            "eligibility_max": hi,
            "model_version": self._bundle.get("version", MODEL_VERSION),
        }


_model: TrustModel | None = None


def get_trust_model(path: str | None = None) -> TrustModel:
    global _model
    if _model is None:
        _model = TrustModel(path)
        _model.load()
    return _model
