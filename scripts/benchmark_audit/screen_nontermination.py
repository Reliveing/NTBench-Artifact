from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "nontermination_screening"


PATTERNS = {
    "loop_explicit": [
        r"\binfinite[ -]+loops?\b",
        r"\bendless[ -]+loops?\b",
        r"\bnon[ -]?terminating[ -]+loops?\b",
        r"\bloops? (?:for(?: )?ever|indefinitely|endlessly)\b",
        r"\b(?:stuck|caught|trapped) in (?:an? )?loops?\b",
        r"\bdead loops?\b",
    ],
    "recursion_explicit": [
        r"\binfinite[ -]+recursion\b",
        r"\brecursive[ -]+loops?\b",
        r"\brecursion(?:error| error)\b",
        r"\bmaximum recursion depth\b",
        r"\btoo much recursion\b",
        r"\brecurses? (?:for(?: )?ever|indefinitely|endlessly)\b",
    ],
    "nontermination_strong": [
        r"\b(?:does not|doesn't|never|fails? to) terminate\b",
        r"\bnever (?:returns?|completes?|finishes?|exits?)\b",
        r"\b(?:runs?|running) (?:for(?: )?ever|indefinitely|endlessly)\b",
        r"\bhangs?\b",
        r"\bhanging\b",
        r"\bhung\b",
        r"\b(?:application|process|program|ui|interface|page) (?:appears? |becomes? )?frozen\b",
        r"\bunresponsive\b",
        r"\bkeeps? (?:running|looping|recursing)\b",
    ],
    "nontermination_weak": [
        r"\bstuck\b",
        r"\btime[ -]?outs?\b",
        r"\btimes? out\b",
    ],
    "loop_context": [
        r"\bwhile\b",
        r"\bfor[ -]+loops?\b",
        r"\bloop(?:ing|s|ed)?\b",
        r"\biterations?\b",
        r"\biterator\b",
        r"\bretr(?:y|ies|ying)\b",
        r"\bpoll(?:ing|s|ed)?\b",
    ],
    "recursion_context": [
        r"\brecurs(?:ion|ive|ively|e|es|ed|ing)\b",
        r"\bcall stack\b",
        r"\bstack overflow\b",
        r"\bbase case\b",
    ],
    "patch_loop_control": [
        r"\bwhile\b",
        r"\bbreak\b",
        r"\bcontinue\b",
        r"\biterations?\b",
        r"\biterators?\b",
        r"\bretr(?:y|ies|ying)\b",
        r"\bvisited\b",
        r"\bseen\b",
        r"\bcycles?\b",
        r"\bmax[_ -]?(?:iter|attempt|retry)",
    ],
    "patch_recursion_control": [
        r"\brecurs(?:ion|ive|ively|e|es|ed|ing)\b",
        r"\brecursionerror\b",
        r"\bbase case\b",
        r"\bvisited\b",
        r"\bseen\b",
        r"\bcycles?\b",
        r"\bcall stack\b",
    ],
}

COMPILED = {
    key: [(pattern, re.compile(pattern, re.IGNORECASE)) for pattern in patterns]
    for key, patterns in PATTERNS.items()
}


def text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(map(str, value))
    return str(value)


def changed_lines(diff: str) -> str:
    lines = []
    for line in text(diff).splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            lines.append(line[1:])
    return "\n".join(lines)


def match_group(value: str, group: str) -> list[str]:
    return [pattern for pattern, rx in COMPILED[group] if rx.search(value)]


def snippets(value: str, groups: list[str], limit: int = 3) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    found = []
    for group in groups:
        for _, rx in COMPILED[group]:
            for match in rx.finditer(value):
                start = max(0, match.start() - 90)
                end = min(len(value), match.end() + 120)
                snippet = value[start:end].strip()
                if snippet not in found:
                    found.append(snippet)
                if len(found) >= limit:
                    return " || ".join(found)
    return " || ".join(found)


def screen(row: dict, dataset: str) -> dict | None:
    issue_fields = ["problem_statement", "requirements", "hints_text"]
    issue = "\n".join(text(row.get(field)) for field in issue_fields if row.get(field))
    patch_changed = changed_lines(row.get("patch", ""))
    test_changed = changed_lines(row.get("test_patch", ""))

    issue_hits = {group: match_group(issue, group) for group in [
        "loop_explicit", "recursion_explicit", "nontermination_strong",
        "nontermination_weak", "loop_context", "recursion_context"
    ]}
    patch_hits = {group: match_group(patch_changed, group) for group in [
        "loop_explicit", "recursion_explicit", "patch_loop_control",
        "patch_recursion_control"
    ]}
    test_hits = {group: match_group(test_changed, group) for group in [
        "loop_explicit", "recursion_explicit", "nontermination_strong"
    ]}

    explicit_issue = bool(issue_hits["loop_explicit"] or issue_hits["recursion_explicit"])
    explicit_patch = bool(patch_hits["loop_explicit"] or patch_hits["recursion_explicit"])
    explicit_test = bool(test_hits["loop_explicit"] or test_hits["recursion_explicit"])
    strong = bool(issue_hits["nontermination_strong"])
    weak = bool(issue_hits["nontermination_weak"])
    issue_loop = bool(issue_hits["loop_explicit"] or issue_hits["loop_context"])
    issue_rec = bool(issue_hits["recursion_explicit"] or issue_hits["recursion_context"])
    patch_loop = bool(patch_hits["loop_explicit"] or patch_hits["patch_loop_control"])
    patch_rec = bool(patch_hits["recursion_explicit"] or patch_hits["patch_recursion_control"])

    score = 0
    reasons = []
    if explicit_issue:
        score += 5
        reasons.append("explicit_issue_phrase")
    if explicit_patch:
        score += 4
        reasons.append("explicit_patch_phrase")
    if explicit_test and (strong or weak or explicit_patch):
        score += 2
        reasons.append("explicit_test_phrase")
    if strong and ((issue_loop or patch_loop) or (issue_rec or patch_rec)):
        score += 3
        reasons.append("strong_symptom_plus_control_context")
    if weak and (patch_loop or patch_rec):
        score += 2
        reasons.append("weak_symptom_plus_patch_control")

    if score < 2:
        return None

    loop_evidence = bool(issue_hits["loop_explicit"] or patch_hits["loop_explicit"] or test_hits["loop_explicit"])
    rec_evidence = bool(issue_hits["recursion_explicit"] or patch_hits["recursion_explicit"] or test_hits["recursion_explicit"])
    if not loop_evidence and not rec_evidence:
        loop_evidence = (strong or weak) and (issue_loop or patch_loop)
        rec_evidence = (strong or weak) and (issue_rec or patch_rec)
    if loop_evidence and rec_evidence:
        preliminary_type = "ambiguous_loop_or_recursion"
    elif rec_evidence:
        preliminary_type = "recursion_candidate"
    elif loop_evidence:
        preliminary_type = "loop_candidate"
    else:
        return None

    issue_lower = issue.lower()
    if "deadlock" in issue_lower and not explicit_issue and not explicit_patch:
        return None

    tier = "A_high" if score >= 5 else "B_medium" if score >= 3 else "C_low"
    issue_patterns = sorted({p for values in issue_hits.values() for p in values})
    patch_patterns = sorted({p for values in patch_hits.values() for p in values})
    test_patterns = sorted({p for values in test_hits.values() for p in values})

    return {
        "dataset": dataset,
        "instance_id": text(row.get("instance_id")),
        "repo": text(row.get("repo")),
        "language": text(row.get("repo_language")) or "python",
        "preliminary_type": preliminary_type,
        "candidate_tier": tier,
        "score": score,
        "selection_reasons": ";".join(reasons),
        "matched_issue_patterns": ";".join(issue_patterns),
        "matched_patch_patterns": ";".join(patch_patterns),
        "matched_test_patterns": ";".join(test_patterns),
        "issue_evidence": snippets(issue, ["loop_explicit", "recursion_explicit", "nontermination_strong", "nontermination_weak", "loop_context", "recursion_context"]),
        "patch_evidence": snippets(patch_changed, ["loop_explicit", "recursion_explicit", "patch_loop_control", "patch_recursion_control"]),
        "test_evidence": snippets(test_changed, ["loop_explicit", "recursion_explicit", "nontermination_strong"]),
        "problem_statement": text(row.get("problem_statement")),
        "review_status": "unreviewed_candidate",
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0]) if rows else [
        "dataset", "instance_id", "repo", "language", "preliminary_type",
        "candidate_tier", "score", "selection_reasons", "matched_issue_patterns",
        "matched_patch_patterns", "matched_test_patterns", "issue_evidence",
        "patch_evidence", "test_evidence", "problem_statement", "review_status"
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    global ROOT, OUT
    parser = argparse.ArgumentParser(description="Screen archived Verified, Pro v2, and SWE-bench-Live Verified snapshots for candidates.")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    ROOT, OUT = args.input_dir, args.output_dir
    OUT.mkdir(parents=True, exist_ok=True)
    datasets = [
        ("SWE-bench Verified", ROOT / "swe-bench-verified.parquet", "swe_bench_verified_candidates.csv"),
        ("SWE-bench Pro v2", ROOT / "swe-bench-pro-v2.parquet", "swe_bench_pro_v2_candidates.csv"),
        ("SWE-bench-Live Verified", ROOT / "swe-bench-live-verified.parquet", "swe_bench_live_verified_candidates.csv"),
    ]
    summaries = []
    for dataset, path, filename in datasets:
        if not path.exists():
            continue
        source_rows = pq.read_table(path).to_pylist()
        candidates = [candidate for row in source_rows if (candidate := screen(row, dataset))]
        candidates.sort(key=lambda row: (-int(row["score"]), row["instance_id"]))
        write_csv(OUT / filename, candidates)
        summaries.append((dataset, len(source_rows), candidates))

    lines = [
        "# Non-termination candidate screening",
        "",
        "This is a high-recall lexical and patch-signal screen, not a final defect classification. Candidates require evidence review.",
        "",
        "| Dataset | Source instances | Candidates | A high | B medium | C low | Loop | Recursion | Ambiguous/unspecified |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset, total, rows in summaries:
        tiers = Counter(row["candidate_tier"] for row in rows)
        types = Counter(row["preliminary_type"] for row in rows)
        loop = types["loop_candidate"]
        recursion = types["recursion_candidate"]
        other = len(rows) - loop - recursion
        lines.append(
            f"| {dataset} | {total} | {len(rows)} | {tiers['A_high']} | {tiers['B_medium']} | {tiers['C_low']} | {loop} | {recursion} | {other} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- A high: explicit non-termination wording or multiple strong evidence channels.",
        "- B medium: strong runtime symptom plus loop/recursion control evidence, or an explicit phrase in the patch.",
        "- C low: weak symptom plus a relevant changed-line signal.",
        "- Matching uses regex word boundaries; substrings such as `latest` do not match `test` or unrelated terms.",
        "- Ordinary long-running services, performance regressions, I/O waits, deadlocks, test harness timeouts, and finite deep recursion may still appear and must be rejected during review.",
    ])
    (OUT / "screening_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
