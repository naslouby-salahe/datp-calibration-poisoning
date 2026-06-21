# CLAUDE.md — datp-cp Repository Instructions

This repository is governed by the datp-cp roadmap:

```text
docs/DATP_CP_Roadmap.md
```

Use the roadmap as the active contract. Existing code, old docs, and old generated artifacts are not automatically canonical.

## Active Vocabulary

Threshold policies:

- `GLOBAL_THRESHOLD`
- `LOCAL_THRESHOLD`
- `CLUSTER_THRESHOLD`

Experiment stages:

- `FINAL_AUDIT`
- `SYNTHETIC_SMOKE`
- `NBAIOT_MAIN`
- `NBAIOT_FULL_OPTIONAL`
- `STRETCH_DIAGNOSTIC_ONLY`

Attack objectives:

- `THRESHOLD_RAISE`
- `THRESHOLD_LOWER`

Source strategies:

- `RANDOM_BENIGN`
- `HIGH_SCORE_BENIGN`
- `LOW_SCORE_BENIGN`

Injection rule:

- `REPLACE_FIXED_BUDGET`

## Scientific Boundary

datp-cp is calibration-channel poisoning only. The poisoning mechanism may modify only benign threshold-calibration scores for eligible clients.

Never alter training data, labels, model weights, gradients, aggregation, test scores, test labels, or test data as part of the attack.

Reservoirs must be victim-local benign calibration scores. Clean calibration arrays must be copied before replacement. AUROC must remain invariant under poisoning.

Forbidden claims include model poisoning, training poisoning, aggregation poisoning, evasion, privacy guarantees, deployment readiness, and broad federated-learning robustness.

## Workflow

Use Makefile targets unless testing a CLI layer directly:

```bash
make help
make check
make datp-cp-clean
make datp-cp-smoke
make datp-cp-dry-run
make datp-cp-run
make datp-cp-report
make status
make audit-results
make clean
```

Run focused tests for narrow edits and broader tests for refactors, scientific-boundary changes, and milestone work.

## Coding Rules

- No backwards compatibility for obsolete values.
- Use enums for closed vocabularies.
- Use frozen dataclasses or typed models for structured configs, manifests, plans, and results.
- Keep scientific constants named and centralized.
- Remove obsolete code instead of commenting it out.
- Do not preserve old names through aliases or wrappers.
- Do not commit or open pull requests unless explicitly instructed.
