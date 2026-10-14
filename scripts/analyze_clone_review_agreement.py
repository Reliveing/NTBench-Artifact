#!/usr/bin/env python3
"""Compute agreement statistics for the 50-record clone-review sample."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABELS = ["type-1", "type-2", "type-3", "N/A"]

def norm(value: str) -> str:
    value = value.strip()
    return value.lower() if value.lower().startswith("type-") else value.upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def metrics(left: list[str], right: list[str]) -> tuple[int, float, float]:
    n = len(left)
    observed_count = sum(a == b for a, b in zip(left, right))
    observed = observed_count / n
    left_counts, right_counts = Counter(left), Counter(right)
    expected = sum(left_counts[label] * right_counts[label] for label in LABELS) / (n * n)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return observed_count, observed, kappa


def confusion(left: list[str], right: list[str]) -> list[list[int]]:
    return [[sum(a == row and b == col for a, b in zip(left, right)) for col in LABELS] for row in LABELS]


def print_matrix(title: str, matrix: list[list[int]]) -> None:
    print(f"\n{title} (rows = first labeler, columns = second labeler)")
    print("label\t" + "\t".join(LABELS))
    for label, values in zip(LABELS, matrix):
        print(label + "\t" + "\t".join(map(str, values)))


def main() -> None:
    review_dir = ROOT / "data" / "rq5" / "clone_review"
    r1_rows = read_csv(review_dir / "reviewer1.csv")
    r2_rows = read_csv(review_dir / "reviewer2.csv")
    llm_rows = read_csv(ROOT / "data" / "rq5" / "clone_classifications.csv")
    r1 = {row["record_id"]: row for row in r1_rows}
    r2 = {row["record_id"]: row for row in r2_rows}
    llm = {row["record_id"]: row for row in llm_rows}
    record_ids = [row["record_id"] for row in r1_rows]
    if set(record_ids) != set(r2) or not set(record_ids) <= set(llm):
        raise ValueError("The reviewer and LLM record sets do not align")

    labels_r1 = [norm(r1[key]["human_label"]) for key in record_ids]
    labels_r2 = [norm(r2[key]["human_label"]) for key in record_ids]
    labels_llm = [norm(llm[key]["classification"]) for key in record_ids]
    for name, left, right in [
        ("Reviewer 1 vs Reviewer 2", labels_r1, labels_r2),
        ("Reviewer 1 vs LLM", labels_r1, labels_llm),
        ("Reviewer 2 vs LLM", labels_r2, labels_llm),
    ]:
        count, agreement, kappa = metrics(left, right)
        print(f"{name}: {count}/50 = {agreement:.1%}; Cohen's kappa = {kappa:.3f}")

    print_matrix("Reviewer 1 vs Reviewer 2", confusion(labels_r1, labels_r2))
    print_matrix("Reviewer 1 vs LLM", confusion(labels_r1, labels_llm))
    print_matrix("Reviewer 2 vs LLM", confusion(labels_r2, labels_llm))

    print("\nPer-LLM-class agreement")
    for label in LABELS:
        indices = [i for i, value in enumerate(labels_llm) if value == label]
        matched_r1 = sum(labels_r1[i] == label for i in indices)
        matched_r2 = sum(labels_r2[i] == label for i in indices)
        print(
            f"{label}: Reviewer 1 {matched_r1}/{len(indices)} = {matched_r1 / len(indices):.1%}; "
            f"Reviewer 2 {matched_r2}/{len(indices)} = {matched_r2 / len(indices):.1%}"
        )

    output = review_dir / "comparison_labels.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "sample_id", "record_id", "reviewer1_label", "reviewer2_label",
            "llm_label",
        ])
        for key, label_r1, label_r2, label_llm in zip(
            record_ids, labels_r1, labels_r2, labels_llm
        ):
            writer.writerow([
                r1[key]["sample_id"], key, label_r1, label_r2,
                label_llm,
            ])
    print(f"\nWrote {output}")


if __name__ == "__main__":
    main()
