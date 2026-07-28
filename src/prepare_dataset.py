from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .dataset_builder import build_dataset
from .schema_analyzer import analyze_schema


def prepare(pairing_report: str, dataset_limit: int, schema_sample: int,
            output_dir: str = "artifacts/dataset", seed: int = 42,
            ratios: tuple[float, float, float] = (0.70, 0.15, 0.15)) -> dict:
    if any(value < 0 for value in ratios) or abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("train/validation/test ratios must be non-negative and sum to 1")
    with Path(pairing_report).open(encoding="utf-8-sig", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    schema = analyze_schema(pairs, sample_limit=schema_sample)
    return build_dataset(
        pairs,
        schema,
        output_dir=output_dir,
        seed=seed,
        ratios=ratios,
        limit=dataset_limit,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairing-report", default="reports/pairing_report.csv")
    parser.add_argument("--dataset-limit", type=int, required=True)
    parser.add_argument("--schema-sample", type=int, default=1000)
    parser.add_argument("--output-dir", default="artifacts/dataset")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    args = parser.parse_args()
    result = prepare(
        args.pairing_report,
        args.dataset_limit,
        args.schema_sample,
        args.output_dir,
        args.seed,
        (args.train_ratio, args.validation_ratio, args.test_ratio),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
