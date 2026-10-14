#!/usr/bin/env python3
"""Select a reproducible, stratified 50-record sample for blind clone review."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "rq5" / "clone_classifications.csv"
OUTPUT = ROOT / "derived" / "clone_review_sample.csv"
SEED = 20261014
QUOTAS = {"type-1": 8, "type-2": 8, "type-3": 20, "N/A": 14}


def configuration_path(row: dict[str, str]) -> Path:
    framework, model, run = row["framework"], row["model"], row["eval"]
    model_dir = {
        "DeepSeek V4 Pro": "deepseek",
        "GPT-5.5": "gpt5.5",
        "Opus 4.8": "opus4.8",
    }[model]
    if framework == "Agentless":
        return Path("Agentless") / f"eval-agentless-{model_dir}"
    if framework == "OpenHands":
        name = {"DeepSeek V4 Pro": "deepseek", "GPT-5.5": "openai", "Opus 4.8": "opus"}[model]
        return Path("OpenHands") / f"openhands+{name}" / run
    if framework == "SWE-agent":
        name = {"DeepSeek V4 Pro": "deepseek", "GPT-5.5": "gpt-5.5", "Opus 4.8": "opus4.8"}[model]
        return Path("mini-swe-agent") / f"sweagent_{name}" / run
    raise ValueError(framework)


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def instance_id(row: dict) -> str:
    return row.get("instance_id") or f"{row['org']}__{row['repo']}-{row['number']}"


def allocate(groups: dict[tuple[str, str], list[dict]], quota: int) -> dict[tuple[str, str], int]:
    keys = sorted(groups)
    allocation = {key: 0 for key in keys}
    if quota >= len(keys):
        for key in keys:
            allocation[key] = 1
    remaining = quota - sum(allocation.values())
    available = {key: len(groups[key]) - allocation[key] for key in keys}
    total = sum(available.values())
    ideals = {key: (available[key] * remaining / total if total else 0) for key in keys}
    for key in keys:
        allocation[key] += int(ideals[key])
    left = quota - sum(allocation.values())
    order = sorted(keys, key=lambda key: (ideals[key] % 1, len(groups[key])), reverse=True)
    for key in order[:left]:
        allocation[key] += 1
    return allocation


def main() -> None:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    rng = random.Random(SEED)
    selected: list[dict[str, str]] = []
    for label, quota in QUOTAS.items():
        groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in records:
            if row["classification"] == label:
                groups[(row["framework"], row["model"])].append(row)
        for key, count in allocate(groups, quota).items():
            selected.extend(rng.sample(groups[key], count))

    cache: dict[Path, tuple[dict[str, dict], dict[str, dict]]] = {}
    payload = []
    for sample_number, row in enumerate(sorted(selected, key=lambda item: item["record_id"]), 1):
        config = configuration_path(row)
        if config not in cache:
            pred_path = ROOT / "data" / "baseline_outputs" / config / "patches" / "all_preds.jsonl"
            gold_config = Path(*config.parts[1:]) if config.parts[0] in {"Agentless", "OpenHands", "mini-swe-agent"} else config
            gold_path = ROOT / "data" / "baseline_outputs" / "evaluation_records" / gold_config / "patches" / "eval-all-python.jsonl"
            predictions = {instance_id(item): item for item in load_jsonl(pred_path)}
            gold = {instance_id(item): item for item in load_jsonl(gold_path)}
            cache[config] = predictions, gold
        predictions, gold = cache[config]
        agent_patch = predictions[row["instance_id"]]["fix_patch"]
        developer_patch = gold[row["instance_id"]]["fix_patch"]
        if hashlib.sha256(agent_patch.encode()).hexdigest() != row["agent_patch_sha256"]:
            raise ValueError(f"Agent patch hash mismatch: {row['record_id']}")
        if hashlib.sha256(developer_patch.encode()).hexdigest() != row["ground_truth_patch_sha256"]:
            raise ValueError(f"Developer patch hash mismatch: {row['record_id']}")
        payload.append({
            "sample_id": f"CR-{sample_number:02d}",
            "record_id": row["record_id"],
            "instance_id": row["instance_id"],
            "framework": row["framework"],
            "model": row["model"],
            "run": row["eval"],
            "agent_patch": agent_patch,
            "developer_patch": developer_patch,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id", "record_id", "instance_id", "framework", "model", "run",
        "agent_patch", "developer_patch",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(payload)
    print(f"Wrote {len(payload)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
