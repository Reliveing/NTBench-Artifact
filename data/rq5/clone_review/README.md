# Clone-classification agreement

This validation examines the LLM-based clone classifications used in RQ5 on a stratified sample of 50 generated-patch and developer-patch pairs.

## Methodology

- **Sample size:** 50 patch pairs selected across all nine approach--model configurations.
- **Reviewers:** two independent reviewers.
- **Categories:** Type-1, Type-2, Type-3, and N/A.
- **Automated classifier:** GPT-5.6 Sol with high reasoning effort.
- **Review material:** the generated patch, developer patch, and shared clone definitions.

### Sample distribution

| LLM category | Count |
| --- | ---: |
| Type-1 | 8 |
| Type-2 | 8 |
| Type-3 | 20 |
| N/A | 14 |

## Agreement results

| Comparison | Observed agreement | Expected agreement | Cohen's kappa |
| --- | ---: | ---: | ---: |
| Reviewer 1 vs. Reviewer 2 | 86.0% | 28.96% | 0.803 |
| Reviewer 1 vs. LLM | 90.0% | 29.44% | 0.858 |
| Reviewer 2 vs. LLM | 84.0% | 28.24% | 0.777 |

The two reviewers agreed on 43 of the 50 patch pairs. Reviewer 1 agreed with the LLM on 45 pairs, and Reviewer 2 agreed on 42.

### Reviewer 1 vs. Reviewer 2

Rows contain Reviewer 1 labels and columns contain Reviewer 2 labels.

|  | Type-1 | Type-2 | Type-3 | N/A |
| --- | ---: | ---: | ---: | ---: |
| Type-1 | 9 | 0 | 0 | 0 |
| Type-2 | 1 | 5 | 0 | 0 |
| Type-3 | 1 | 0 | 16 | 4 |
| N/A | 0 | 0 | 1 | 13 |

### Reviewer 1 vs. LLM

Rows contain Reviewer 1 labels and columns contain LLM labels.

|  | Type-1 | Type-2 | Type-3 | N/A |
| --- | ---: | ---: | ---: | ---: |
| Type-1 | 7 | 2 | 0 | 0 |
| Type-2 | 0 | 6 | 0 | 0 |
| Type-3 | 1 | 0 | 19 | 1 |
| N/A | 0 | 0 | 1 | 13 |

### Reviewer 2 vs. LLM

Rows contain Reviewer 2 labels and columns contain LLM labels.

|  | Type-1 | Type-2 | Type-3 | N/A |
| --- | ---: | ---: | ---: | ---: |
| Type-1 | 8 | 3 | 0 | 0 |
| Type-2 | 0 | 5 | 0 | 0 |
| Type-3 | 0 | 0 | 16 | 1 |
| N/A | 0 | 0 | 4 | 13 |

## Agreement by clone type

The denominator is the number of samples assigned to each category by the LLM.

| Clone type | Samples | Reviewer 1 | Reviewer 2 |
| --- | ---: | ---: | ---: |
| Type-1 | 8 | 7/8 (87.5%) | 8/8 (100.0%) |
| Type-2 | 8 | 6/8 (75.0%) | 5/8 (62.5%) |
| Type-3 | 20 | 19/20 (95.0%) | 16/20 (80.0%) |
| N/A | 14 | 13/14 (92.9%) | 13/14 (92.9%) |

## Disagreement analysis

The reviewers disagreed on seven patch pairs. Five disagreements concerned the Type-3/N/A boundary, one concerned Type-1/Type-2, and one concerned Type-1/Type-3. The reviewers agreed with each other but differed from the LLM on three pairs: one Type-3/N/A case and two Type-1/Type-2 cases.

Overall, the LLM agrees with each reviewer on at least 84.0% of the sample, with Cohen's kappa ranging from 0.777 to 0.858. Type-1, Type-3, and N/A show consistently high agreement. Type-2 is less stable because small literal or textual differences can shift the boundary between Type-1 and Type-2, while the main broader disagreement lies between structurally related Type-3 patches and N/A alternatives.

## Released files

- `review_sample_50.xlsx`: the sampled patch pairs and review instructions.
- `reviewer1.csv`: Reviewer 1 labels and rationales.
- `reviewer2.csv`: Reviewer 2 labels and rationales.
- `comparison_labels.csv`: aligned Reviewer 1, Reviewer 2, and LLM labels used to reproduce the comparisons.

Run `python scripts/analyze_clone_review_agreement.py` from the repository root to reproduce the agreement statistics and regenerate `comparison_labels.csv`.

Run `python scripts/select_clone_review_sample.py` to reproduce the stratified blind sample as `derived/clone_review_sample.csv`.
