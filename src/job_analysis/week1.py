"""Run all implemented week-one data, visualization, and modeling stages."""

import argparse
import json
from pathlib import Path

from .cleaning import DEFAULT_INPUT_DIR, PROJECT_ROOT, run as run_cleaning
from .modeling import run as run_modeling
from .visualization import run as run_visualization


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete week-one analysis workflow")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--sample-size", type=int)
    args = parser.parse_args()
    if args.sample_size:
        audit = run_cleaning(args.input_dir, PROJECT_ROOT, args.sample_size)
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return
    audit = run_cleaning(args.input_dir, PROJECT_ROOT)
    figures = run_visualization()
    metrics = run_modeling()
    print(
        json.dumps(
            {
                "cleaning": audit,
                "figure_count": len(figures),
                "models": json.loads(metrics.to_json(orient="records")),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
