"""Generate repository counts and an optional manuscript table from final labels."""
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = (
    "IL_LOGICAL_ERROR", "IL_GENERAL_PROGRAMMING_ERROR",
    "IR_INCORRECT_RECURSION_DESIGN", "IR_UNEXPECTED_RECURSION",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex", type=Path, help="Optional output LaTeX table")
    args = parser.parse_args()
    with (ROOT / "data/rq1/instance_characteristics.csv").open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    assert len(records) == len({r["instance_id"] for r in records}) == 53
    counts = defaultdict(Counter)
    for row in records:
        label = row["four_group_label"]
        assert label in LABELS, label
        counts[row["instance_id"].split("#")[0]][label] += 1
    assert len(counts) == 13
    rows = [dict(repository=repo, total=sum(counts[repo].values()),
                 **{label: counts[repo][label] for label in LABELS}) for repo in sorted(counts, key=str.lower)]
    out = ROOT / "derived/repository_defect_distribution.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if args.tex:
        lines = [r"\begin{table}[!htbp]", r"\centering", r"\small",
                 r"\caption{Repository-level distribution of the four defect categories in NTBench.}",
                 r"\label{tab:repository-defects}", r"\begin{tabular}{lrrrrr}", r"\toprule",
                 r"Repository & Instances & IL-L & IL-G & IR-D & IR-U \\", r"\midrule"]
        for row in rows:
            lines.append(" & ".join(str(row[k]) for k in row) + r" \\")
        totals = [sum(row[k] for row in rows) for k in ("total", *LABELS)]
        lines += [r"\midrule", "Total & " + " & ".join(map(str, totals)) + r" \\",
                  r"\bottomrule", r"\end{tabular}", r"\par\smallskip",
                  r"\begin{minipage}{0.95\linewidth}\footnotesize",
                  "IL-L: loop logical errors; IL-G: loop general programming errors; "
                  "IR-D: incorrect recursion design; IR-U: unexpected recursion.",
                  r"\end{minipage}", r"\end{table}"]
        args.tex.parent.mkdir(parents=True, exist_ok=True)
        args.tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
