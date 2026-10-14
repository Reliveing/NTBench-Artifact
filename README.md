# NTBench Study Artifact

This directory contains the processed data, review records, and analysis scripts used in the NTBench paper. Because the complete agent execution trajectories are substantially larger than the processed artifact, they are distributed with the benchmark through the [NTBench Hugging Face repository](https://huggingface.co/datasets/liheng520/NTBench). This GitHub artifact contains the generated patches, evaluator logs and reports, derived tables, review records, and data-processing scripts.

- `data/baseline`: evaluated results for the nine configurations.
- `data/baseline_outputs`: generated baseline patches and evaluator records, including per-instance logs, evaluated patches, and reports under `evaluation_records/`.
- `data/benchmark_construction`: repository-level screening records supporting the benchmark construction pipeline in Figure 1, including the independent review reasons for the four excluded preliminary candidates.
- `data/rq1`: benchmark characteristics and review records supporting the final defect labels.
- `data/benchmark_audit`: screening candidates and final causal-review decisions for SWE-bench Verified, SWE-bench-Live Verified, SWE-bench Pro v2, and Multi-SWE-bench.
- `data/rq4`: the 390 failure-outcome classifications and the final review records for the 97 outcomes initially labeled U.
- `data/guided_retry`: guided-retry patches, logs, and evaluation results.
- `data/rq5`: patch-distance, clone, and atypical-success records. The `clone_review/` directory contains the 50-pair review sample, two independent review records, and detailed agreement results.
- `scripts`: release preparation, aggregation, validation, and benchmark-audit scripts.

## Clone-classification validation

We validated the LLM-based Type-1/Type-2/Type-3/N/A classification on a stratified sample of 50 successful patches. Two reviewers independently compared each generated patch with its developer patch using the same clone definitions. Their judgments show substantial agreement with each other and with the LLM classifications.

| Comparison | Agreement | Cohen's kappa |
| --- | ---: | ---: |
| Reviewer 1 vs. Reviewer 2 | 43/50 (86.0%) | 0.803 |
| Reviewer 1 vs. LLM | 45/50 (90.0%) | 0.858 |
| Reviewer 2 vs. LLM | 42/50 (84.0%) | 0.777 |

The three comparisons show high agreement, with the remaining differences concentrated at the Type-1/Type-2 and Type-3/N/A boundaries. The complete methodology, confusion matrices, disagreement analysis, and review records are available in [`data/rq5/clone_review/`](data/rq5/clone_review/README.md). The statistics can be reproduced with `scripts/analyze_clone_review_agreement.py`.

Run from the repository root:

```bash
python artifact/scripts/summarize_results.py
python artifact/scripts/validate_release.py
python artifact/scripts/summarize_benchmark_composition.py
```
