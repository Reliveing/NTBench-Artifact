"""Recompute compact result summaries from the released CSV files."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "derived"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def baseline_summary() -> list[dict[str, object]]:
    inputs = [
        ("Agentless", "agentless_results.csv"),
        ("OpenHands", "openhands_results.csv"),
        ("mini-swe-agent", "mini_swe_agent_results.csv"),
    ]
    output = []
    for framework, name in inputs:
        rows = read_csv(DATA / "baseline" / name)
        prefixes = {column.rsplit("_", 1)[0] for column in rows[0] if column != "instance_id"}
        for prefix in sorted(prefixes):
            columns = [c for c in rows[0] if c == prefix or c.startswith(prefix + "_")]
            total = len(rows) * len(columns)
            successes = sum(int(row[c]) for row in rows for c in columns)
            solved = sum(any(row[c] == "1" for c in columns) for row in rows)
            output.append(
                {
                    "framework": framework,
                    "model_column_prefix": prefix,
                    "runs_per_instance": len(columns),
                    "successes": successes,
                    "outcomes": total,
                    "pass_at_1_percent": f"{100 * successes / total:.2f}",
                    "solved_instances": solved,
                    "empirical_pass_at_3_percent": f"{100 * solved / len(rows):.2f}" if len(columns) == 3 else "",
                }
            )
    return output


def grouped_counts(path: Path, keys: list[str], value: str) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], Counter[str]] = {}
    for row in read_csv(path):
        key = tuple(row[k] for k in keys)
        groups.setdefault(key, Counter())[row[value] or "N/A"] += 1
    output = []
    all_values = sorted({label for counts in groups.values() for label in counts})
    for key, counts in sorted(groups.items()):
        output.append(
            {
                **dict(zip(keys, key)),
                "total": sum(counts.values()),
                **{label: counts[label] for label in all_values},
            }
        )
    return output


def main() -> None:
    write_csv(OUT / "baseline_summary.csv", baseline_summary())
    write_csv(
        OUT / "failure_outcome_summary.csv",
        grouped_counts(DATA / "rq4/all_failure_outcomes.csv", ["framework", "model"], "primary_outcome"),
    )
    write_csv(
        OUT / "guided_retry_summary.csv",
        grouped_counts(DATA / "guided_retry/trajectory_results.csv", ["initial_outcome"], "final_observed_state"),
    )
    write_csv(
        OUT / "clone_summary.csv",
        grouped_counts(DATA / "rq5/clone_classifications.csv", ["framework", "model"], "classification"),
    )
    print(f"Wrote four summaries to {OUT}")


if __name__ == "__main__":
    main()
