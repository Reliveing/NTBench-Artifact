from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent / "Multi-SWE-bench"
CANDIDATES = Path(__file__).resolve().parent / "nontermination_screening" / "multi_swe_bench_candidates.csv"


def main() -> None:
    global ROOT, CANDIDATES
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--brief", action="store_true")
    args = parser.parse_args()
    ROOT, CANDIDATES = args.input_dir, args.candidates

    candidates = pd.read_csv(CANDIDATES).iloc[args.start : args.start + args.count]
    wanted = set(candidates["instance_id"].astype(str))
    records: dict[str, dict] = {}
    for path in ROOT.glob("*/*.jsonl"):
        if path.parent.name == "python":
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                instance_id = str(
                    row.get("instance_id")
                    or f"{row.get('org')}__{row.get('repo')}-{row.get('number')}"
                )
                if instance_id in wanted:
                    row["_language"] = path.parent.name
                    records[instance_id] = row

    for instance_id in candidates["instance_id"].astype(str):
        row = records[instance_id]
        print("\n" + "=" * 100)
        print("INSTANCE:", instance_id)
        print("LANGUAGE:", row["_language"])
        print("TITLE:", row.get("title", ""))
        if args.brief:
            issue = json.dumps(row.get("resolved_issues"), ensure_ascii=False)
            print("BODY:", str(row.get("body", ""))[:1800])
            print("RESOLVED ISSUES:", issue[:5000])
            pattern = re.compile(
                r"infinite|endless|recurs|stack overflow|hang|hung|freeze|frozen|"
                r"unresponsive|while|break|continue|retry|poll|visited|cycle|timeout",
                re.IGNORECASE,
            )
            patch_lines = str(row.get("fix_patch", "")).splitlines()
            indexes = [i for i, line in enumerate(patch_lines) if pattern.search(line)]
            keep = sorted({j for i in indexes for j in range(max(0, i - 3), min(len(patch_lines), i + 4))})
            print("PATCH SIGNAL CONTEXT:")
            previous = -2
            for i in keep:
                if i > previous + 1:
                    print("...")
                print(patch_lines[i])
                previous = i
            continue
        print("BODY:\n", str(row.get("body", ""))[:7000])
        print("RESOLVED ISSUES:\n", json.dumps(row.get("resolved_issues"), ensure_ascii=False)[:7000])
        print("FIX PATCH:\n", str(row.get("fix_patch", ""))[:14000])
        print("TEST PATCH:\n", str(row.get("test_patch", ""))[:7000])


if __name__ == "__main__":
    main()
