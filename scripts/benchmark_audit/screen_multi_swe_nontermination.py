from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "Multi-SWE-bench"
OUT = Path(__file__).resolve().parent / "nontermination_screening"

EXPLICIT_LOOP = re.compile(
    r"\b(?:infinite[ -]+loops?|endless[ -]+loops?|non[ -]?terminating[ -]+loops?|"
    r"loops? (?:forever|indefinitely|endlessly)|(?:stuck|caught|trapped) in (?:an? )?loops?)\b",
    re.IGNORECASE,
)
EXPLICIT_RECURSION = re.compile(
    r"\b(?:infinite[ -]+recursion|recursive[ -]+loops?|recursion\s*error|"
    r"maximum recursion depth|too much recursion|recurses? (?:forever|indefinitely|endlessly)|"
    r"stack overflow)\b",
    re.IGNORECASE,
)
STRONG_SYMPTOM = re.compile(
    r"\b(?:hangs?|hanging|hung|freezes?|frozen|unresponsive|"
    r"never (?:returns?|finishes?|completes?|exits?|terminates?)|"
    r"(?:does not|doesn't|fails? to) terminate|keeps? (?:running|looping|recursing))\b",
    re.IGNORECASE,
)
PATCH_CONTROL = re.compile(
    r"\b(?:while|loops?|break|continue|retr(?:y|ies|ying)|poll(?:s|ed|ing)?|"
    r"recurs(?:ion|ive|ively|e|es|ed|ing)|visited|seen|cycles?|"
    r"max[_ -]?(?:iter|attempt|retry)|timeouts?)\b",
    re.IGNORECASE,
)
BROAD_ISSUE_SIGNAL = re.compile(
    r"\b(?:loops?|looped|looping|recurs(?:e|es|ed|ing|ion|ive|ively)|"
    r"hangs?|hanging|hung|freezes?|frozen|stuck|spins?|spinning|livelock|deadlock|"
    r"forever|indefinitely|endlessly|stack overflow|too many updates|"
    r"maximum update depth|100% cpu|out of memory|oom)\b",
    re.IGNORECASE,
)


def flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def changed_lines(diff: object) -> str:
    result = []
    for line in flatten(diff).splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            result.append(line[1:])
    return "\n".join(result)


def snippet(text: str, match: re.Match[str] | None) -> str:
    if match is None:
        return ""
    start = max(0, match.start() - 120)
    end = min(len(text), match.end() + 220)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def main() -> None:
    global ROOT, OUT
    parser = argparse.ArgumentParser(description="Screen archived Multi-SWE-bench non-Python tasks.")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    ROOT, OUT = args.input_dir, args.output_dir
    if not list(ROOT.glob("*/*.jsonl")):
        parser.error("Expected language subdirectories containing JSONL snapshots")
    rows: list[dict[str, object]] = []
    broad_rows: list[dict[str, object]] = []
    source_count = 0
    for path in sorted(ROOT.glob("*/*.jsonl")):
        language = path.parent.name
        if language == "python":
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                source_count += 1
                row = json.loads(line)
                issue = "\n".join(
                    flatten(row.get(field))
                    for field in ("title", "body", "resolved_issues")
                )
                patch = changed_lines(row.get("fix_patch"))
                test = changed_lines(row.get("test_patch"))
                broad_matches = sorted({m.group(0).lower() for m in BROAD_ISSUE_SIGNAL.finditer(issue)})
                if broad_matches:
                    broad_rows.append(
                        {
                            "language": language,
                            "instance_id": row.get("instance_id")
                            or f"{row.get('org')}__{row.get('repo')}-{row.get('number')}",
                            "title": row.get("title", ""),
                            "signals": ";".join(broad_matches),
                            "evidence": snippet(issue, BROAD_ISSUE_SIGNAL.search(issue)),
                        }
                    )
                issue_loop = EXPLICIT_LOOP.search(issue)
                issue_recursion = EXPLICIT_RECURSION.search(issue)
                patch_loop = EXPLICIT_LOOP.search(patch)
                patch_recursion = EXPLICIT_RECURSION.search(patch)
                test_loop = EXPLICIT_LOOP.search(test)
                test_recursion = EXPLICIT_RECURSION.search(test)
                symptom = STRONG_SYMPTOM.search(issue)
                patch_control = PATCH_CONTROL.search(patch)

                explicit_issue = bool(issue_loop or issue_recursion)
                explicit_patch = bool(patch_loop or patch_recursion)
                explicit_test = bool(test_loop or test_recursion)
                symptom_control = bool(symptom and patch_control)
                if not (explicit_issue or explicit_patch or explicit_test or symptom_control):
                    continue

                score = (
                    (5 if explicit_issue else 0)
                    + (4 if explicit_patch else 0)
                    + (2 if explicit_test else 0)
                    + (3 if symptom_control else 0)
                )
                first_match = (
                    issue_loop
                    or issue_recursion
                    or symptom
                    or patch_loop
                    or patch_recursion
                    or test_loop
                    or test_recursion
                )
                source_text = issue if first_match in (issue_loop, issue_recursion, symptom) else patch
                rows.append(
                    {
                        "language": language,
                        "instance_id": row.get("instance_id")
                        or f"{row.get('org')}__{row.get('repo')}-{row.get('number')}",
                        "org": row.get("org", ""),
                        "repo": row.get("repo", ""),
                        "pr_number": row.get("number", ""),
                        "title": row.get("title", ""),
                        "score": score,
                        "explicit_issue_loop": int(bool(issue_loop)),
                        "explicit_issue_recursion": int(bool(issue_recursion)),
                        "explicit_patch_loop": int(bool(patch_loop)),
                        "explicit_patch_recursion": int(bool(patch_recursion)),
                        "explicit_test_loop": int(bool(test_loop)),
                        "explicit_test_recursion": int(bool(test_recursion)),
                        "strong_symptom_plus_patch_control": int(symptom_control),
                        "evidence": snippet(source_text, first_match),
                    }
                )

    rows.sort(key=lambda item: (-int(item["score"]), str(item["instance_id"])))
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "multi_swe_bench_candidates.csv"
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    broad_output = OUT / "multi_swe_bench_broad_issue_signals.csv"
    with broad_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(broad_rows[0]) if broad_rows else [])
        if broad_rows:
            writer.writeheader()
            writer.writerows(broad_rows)
    print(
        f"source_non_python={source_count} candidates={len(rows)} broad={len(broad_rows)} "
        f"output={output} broad_output={broad_output}"
    )


if __name__ == "__main__":
    main()
