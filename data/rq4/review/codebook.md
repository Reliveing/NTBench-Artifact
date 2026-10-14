# RQ4 Failure-Outcome Review Codebook

The unit of analysis is one unsuccessful evaluated repair outcome: one selected result for each Agentless model--instance pair and one run for each OpenHands or mini-swe-agent model--instance pair. Each outcome receives one primary label.

- **O1 -- Patch delivery or application failure.** No patch is delivered, the submitted patch is empty, or it cannot be applied to the benchmark revision.
- **O2 -- Target failure retained.** A concrete target case retains the original non-terminating behavior, with no evidence that another required target case was repaired.
- **O3 -- Incomplete required coverage.** Evidence identifies both a repaired required case and another required case that remains unresolved.
- **O4 -- Incorrect replacement behavior.** The target no longer fails in the original way, but produces an incorrect value, structure, exception, or other observable result.
- **O5 -- Collateral regression.** The patch breaks concrete behavior that was valid before the repair and lies outside the target repair requirement.
- **U -- Unresolved.** The available artifacts do not establish a concrete behavioral witness for O1--O5, or the evidence is missing or conflicting.

When several outcomes apply, the primary-label order is O1, O5, O4, O3, O2. Textual difference from the developer patch is not failure evidence. O2--O5 require an identified input, execution path, test result, or static behavioral counterexample. `review_records.csv` reports the final review result for the 97 records initially labeled U, including the evidence basis and concise reason for each retained or revised label.
