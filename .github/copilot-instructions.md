# GitHub Copilot Instructions — datp-cp

The active project is datp-cp: calibration-channel poisoning of federated threshold personalization in IoT anomaly detection.

Read these first:

- `docs/DATP_CP_Roadmap.md`
- `.rework/ROADMAP_CONTRACT.md`
- `CLAUDE.md`

## Canonical Workflow

Use Makefile targets for repository workflows:

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

## Canonical Terms

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

## Scientific Rules

- Poisoning is calibration-channel only.
- Training data, labels, model weights, aggregation, test scores, test labels, and test data remain clean.
- Reservoirs are victim-local benign calibration scores.
- Clean arrays are copied before replacement.
- Seeds use `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])`.
- AUROC must remain invariant under poisoning.
- Do not introduce claims about model poisoning, training poisoning, evasion, privacy, deployment, or broad federated-learning robustness.

## Code Rules

- No backwards compatibility for obsolete values.
- Delete obsolete code instead of keeping aliases.
- Use typed enums for closed vocabularies.
- Use frozen dataclasses or typed models for configs, manifests, plans, and results.
- Keep scientific constants centralized.
- Run focused tests for the files you change and `make check` for broad refactors.
