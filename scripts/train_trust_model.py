#!/usr/bin/env python3
"""Train thin-file trust model and write joblib artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from finehelper_api.ml.trust.model import train_and_save


def main() -> None:
    parser = argparse.ArgumentParser(description="Train TrustMesh alternate credit model")
    parser.add_argument(
        "--out",
        default="apps/api/finehelper_api/ml/artifacts/trust_model.joblib",
        help="Output joblib path",
    )
    parser.add_argument("--n", type=int, default=600, help="Synthetic training rows")
    args = parser.parse_args()
    path = train_and_save(args.out, n=args.n)
    print(f"Wrote trust model -> {Path(path).resolve()}")


if __name__ == "__main__":
    main()
