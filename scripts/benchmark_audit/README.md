# Benchmark audit

This directory contains the scripts used to screen four repository-level repair benchmarks for causal infinite-loop and infinite-recursion defects. Screening produces candidate lists; the accompanying review tables record the final inclusion decisions after inspection of issue descriptions, patches, tests, and available execution evidence.

## Released records

| Benchmark | Screening candidates | Final decisions | Included |
| --- | --- | --- | ---: |
| SWE-bench Verified | `data/benchmark_audit/swe_bench_verified_candidates.csv` | `data/benchmark_audit/strict_causal_review.csv` | 0 |
| SWE-bench-Live Verified | `data/benchmark_audit/swe_bench_live_verified_candidates.csv` | `data/benchmark_audit/swe_bench_live_verified_strict_review.csv` | 1 |
| SWE-bench Pro v2 | `data/benchmark_audit/swe_bench_pro_v2_candidates.csv` | `data/benchmark_audit/strict_causal_review.csv` | 1 |
| Multi-SWE-bench | `data/benchmark_audit/multi_swe_bench_candidates.csv` | `data/benchmark_audit/multi_swe_bench_strict_review.csv` | 7 |

`strict_causal_review.csv` uses the `dataset` column to distinguish Verified from Pro v2. The `include_as_infinite_loop_or_recursion` field is the final binary inclusion decision.

The audit finds nine causal non-termination tasks across the four released scopes. `derived/swe_bench_live_verified_overlap.json` records the overlap audit between SWE-bench-Live Verified and archived SWE-bench Verified. It reports no shared task by instance ID, repository and pull request, normalized patch, or normalized test patch. The paper reports the released 500-row SWE-bench-Live Verified snapshot.

## Snapshot scopes

The audited scopes contain 500 Verified tasks, 642 Pro v2 tasks, 500 SWE-bench-Live Verified rows (499 unique task IDs), and 1,737 non-Python Multi-SWE-bench tasks. The Multi-SWE-bench script skips its Python subdirectory, whose 500 tasks duplicate the archived Verified release. Raw third-party dataset snapshots are not redistributed in this artifact.

## Reproduction

Install `pyarrow` for Parquet screening and `pandas` for the Multi-SWE-bench inspection helper. Place `swe-bench-verified.parquet`, `swe-bench-pro-v2.parquet`, and `swe-bench-live-verified.parquet` under `SNAPSHOTS`. Place the archived Multi-SWE-bench JSONL files under language subdirectories of `MULTI_SNAPSHOT`, then run:

```bash
python scripts/benchmark_audit/screen_nontermination.py --input-dir SNAPSHOTS --output-dir SCREEN_OUTPUT
python scripts/benchmark_audit/screen_multi_swe_nontermination.py --input-dir MULTI_SNAPSHOT --output-dir SCREEN_OUTPUT
python scripts/benchmark_audit/inspect_multi_swe_candidates.py --input-dir MULTI_SNAPSHOT --candidates SCREEN_OUTPUT/multi_swe_bench_candidates.csv --start 0 --count 10
python scripts/benchmark_audit/compare_verified_snapshots.py SNAPSHOTS/swe-bench-live-verified.parquet SNAPSHOTS/swe-bench-verified.parquet --output derived/swe_bench_live_verified_overlap.json
```

The scripts reproduce candidate generation and overlap statistics. The released strict-review CSV files preserve the final inspection decisions used for the paper's benchmark-coverage counts.
