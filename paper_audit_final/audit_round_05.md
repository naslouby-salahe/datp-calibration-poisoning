# Audit Round 05: Harsh Reviewer Loophole Audit

## Reviewer A: Scientific Method
- Top risk: score-level proxy could be mistaken for raw-traffic attack.
- Answered: abstract, threat model, discussion, conclusion.
- Fix needed: NO; limitation is explicit.

## Reviewer B: FL/Security
- Top risk: attack could be confused with training/model/aggregation poisoning.
- Answered: introduction, threat model, background, Fig. 1.
- Fix needed: NO; contrasts are explicit and bounded.

## Reviewer C: Statistics/Results
- Top risk: seed-level versus victim-seed independence.
- Answered: method statistical analysis and table captions; CIs over 10 seed-level aggregates.
- Fix needed: NO.

## Reviewer D: LNCS/Formatting
- Top risk: dense tables and small figures.
- Answered: visual audit confirms readability.
- Fix needed: NO.

## Reviewer E: Skeptical Conference Reviewer
- Top risk: fixed-budget injection count mismatch with protocol.
- Answered after fix: threat model now matches roadmap and implementation.
- Fix needed: YES; applied in `paper/sections/threat_model.tex`.

## Rejected Reviewer Requests
1. REJECTED: New raw-traffic attack realization.
2. REJECTED: New defenses or robust aggregation experiments.
3. REJECTED: New datasets.
4. REJECTED: Multi-client collusion experiments.
5. REJECTED: Related-work comparison table if it increases page count.

## Result
PASS. Main residual reviewer risk is narrowness, but the paper states the narrow scope clearly and repeatedly.
