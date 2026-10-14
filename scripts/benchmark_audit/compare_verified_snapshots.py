"""Check identity and exact-content overlap between two benchmark snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq


def normalize(value: object) -> str:
    return "\n".join(line.strip() for line in str(value or "").splitlines() if line.strip())


def digest(value: object) -> str:
    return hashlib.sha256(normalize(value).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("live", type=Path)
    parser.add_argument("verified", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    live = pq.read_table(args.live).to_pylist()
    verified = pq.read_table(args.verified).to_pylist()
    live_ids = Counter(str(row["instance_id"]) for row in live)
    verified_ids = Counter(str(row["instance_id"]) for row in verified)
    result = {
        "live_rows": len(live),
        "live_unique_instance_ids": len(live_ids),
        "verified_rows": len(verified),
        "verified_unique_instance_ids": len(verified_ids),
        "duplicate_live_instance_ids": {key: count for key, count in live_ids.items() if count > 1},
        "exact_instance_id_overlap": len(live_ids.keys() & verified_ids.keys()),
        "exact_repo_pr_overlap": len(
            {(str(row.get("repo")), str(row.get("pull_number"))) for row in live}
            & {(str(row.get("repo")), str(row.get("pull_number"))) for row in verified}
        ),
        "exact_normalized_patch_overlap": len(
            {digest(row.get("patch")) for row in live} & {digest(row.get("patch")) for row in verified}
        ),
        "exact_normalized_test_patch_overlap": len(
            {digest(row.get("test_patch")) for row in live}
            & {digest(row.get("test_patch")) for row in verified}
        ),
        "shared_repositories": sorted(
            {str(row.get("repo")) for row in live} & {str(row.get("repo")) for row in verified}
        ),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
