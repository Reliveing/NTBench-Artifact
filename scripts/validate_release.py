"""Validate the identities and headline counts used in the NTBench paper."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    rq1 = read_csv(DATA / "rq1/instance_characteristics.csv")
    assert len(rq1) == len({r["instance_id"] for r in rq1}) == 53
    assert Counter(r["behavior_type"] for r in rq1) == Counter({"Infinite loop": 28, "Infinite recursion": 25})

    successes = 0
    failures = 0
    expected_rows = {
        "agentless_results.csv": 53,
        "openhands_results.csv": 53,
        "mini_swe_agent_results.csv": 53,
    }
    for name, row_count in expected_rows.items():
        rows = read_csv(DATA / "baseline" / name)
        assert len(rows) == row_count
        result_columns = [c for c in rows[0] if c != "instance_id"]
        for row in rows:
            for column in result_columns:
                assert row[column] in {"0", "1"}
                successes += int(row[column])
                failures += 1 - int(row[column])
    assert (successes, failures) == (723, 390)

    expected_main_results = {
        ("agentless_results.csv", "deepseek"): (20, 20, None),
        ("agentless_results.csv", "gpt5.5"): (26, 26, None),
        ("agentless_results.csv", "opus4.8"): (24, 24, None),
        ("openhands_results.csv", "deepseekv4pro"): (103, 40, (13, 6, 5, 29)),
        ("openhands_results.csv", "gpt5.5"): (110, 39, (14, 2, 3, 34)),
        ("openhands_results.csv", "opus4.8"): (111, 42, (11, 4, 7, 31)),
        ("mini_swe_agent_results.csv", "deepseekv4pro"): (110, 39, (14, 1, 5, 33)),
        ("mini_swe_agent_results.csv", "gpt5.5"): (103, 37, (16, 3, 2, 32)),
        ("mini_swe_agent_results.csv", "opus4.8"): (116, 40, (13, 1, 2, 37)),
    }
    for (name, prefix), (expected_successes, expected_solved, expected_histogram) in expected_main_results.items():
        rows = read_csv(DATA / "baseline" / name)
        columns = [c for c in rows[0] if c == prefix or c.startswith(prefix + "_")]
        run_counts = [sum(int(row[column]) for column in columns) for row in rows]
        assert sum(run_counts) == expected_successes
        assert sum(count > 0 for count in run_counts) == expected_solved
        if expected_histogram is not None:
            assert tuple(Counter(run_counts)[count] for count in range(4)) == expected_histogram

    outcomes = read_csv(DATA / "rq4/all_failure_outcomes.csv")
    assert len(outcomes) == 390
    assert Counter(r["primary_outcome"] for r in outcomes) == Counter(
        {"O1": 22, "O2": 134, "O3": 100, "O4": 120, "O5": 11, "U": 3}
    )

    guided = read_csv(DATA / "guided_retry/trajectory_results.csv")
    assert len(guided) == 39
    assert Counter(r["final_observed_state"] for r in guided) == Counter(
        {
            "success": 2,
            "partial_f2p_with_p2f": 1,
            "terminated_but_f2p_failed": 25,
            "nontermination_or_recursion_retained": 11,
        }
    )

    distance_runs = read_csv(DATA / "rq5/distance_success_runs.csv")
    distance_points = read_csv(DATA / "rq5/distance_instance_configuration_means.csv")
    assert len(distance_runs) == 723
    assert len(distance_points) == 307
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in distance_runs:
        grouped[row["method"], row["model"], row["instance_id"]].append(float(row["edit_distance"]))
    assert len(grouped) == 307
    for row in distance_points:
        values = grouped[row["method"], row["model"], row["instance_id"]]
        assert abs(float(row["edit_distance"]) - sum(values) / len(values)) < 1e-8

    clones = read_csv(DATA / "rq5/clone_classifications.csv")
    assert len(clones) == 723
    assert Counter(r["classification"] or "N/A" for r in clones) == Counter(
        {"type-1": 63, "type-2": 12, "type-3": 478, "N/A": 170}
    )

    clone_review = read_csv(DATA / "rq5/clone_review/comparison_labels.csv")
    assert len(clone_review) == 50
    assert len({r["sample_id"] for r in clone_review}) == 50
    assert len({r["record_id"] for r in clone_review}) == 50
    assert {r["record_id"] for r in clone_review} <= {r["record_id"] for r in clones}
    valid_clone_labels = {"type-1", "type-2", "type-3", "N/A"}

    def normalize_clone_label(value: str) -> str:
        return value.lower() if value.lower().startswith("type-") else value.upper()

    normalized_review = [
        {
            key: normalize_clone_label(row[key])
            for key in ("reviewer1_label", "reviewer2_label", "llm_label")
        }
        for row in clone_review
    ]
    assert all(set(row.values()) <= valid_clone_labels for row in normalized_review)
    assert sum(r["reviewer1_label"] == r["reviewer2_label"] for r in normalized_review) == 43
    assert sum(r["reviewer1_label"] == r["llm_label"] for r in normalized_review) == 45
    assert sum(r["reviewer2_label"] == r["llm_label"] for r in normalized_review) == 42

    atypical = read_csv(DATA / "rq5/atypical_points.csv")
    assert len(atypical) == 28
    assert len({r["instance_id"] for r in atypical}) == 11

    summary = {
        "status": "PASS",
        "instances": 53,
        "baseline_outcomes": successes + failures,
        "successful_outcomes": successes,
        "unsuccessful_outcomes": failures,
        "failure_labels": dict(Counter(r["primary_outcome"] for r in outcomes)),
        "guided_retries": len(guided),
        "distance_points": len(distance_points),
        "clone_classifications": len(clones),
        "clone_review_sample": len(clone_review),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
