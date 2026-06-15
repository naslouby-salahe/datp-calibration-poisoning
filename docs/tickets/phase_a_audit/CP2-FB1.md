# CP2-FB1 — Fallback: Clean Score Artifacts Fail Provenance Audit

**Phase:** A — Read-only audit (fallback)
**Type:** scientific-drift / implementation (conditional)
**Priority:** critical
**Status:** not started (CONDITIONAL — do NOT activate without trigger)
**Dependencies:** CP2-T007
**Blocks:** —
**Expected test level:** integration, e2e
**Graphify required:** conditional
**Paper notes required:** yes

## 1. Purpose
**CONDITIONAL.** Activate only if CP2-T007 cannot confirm conference-faithful
(E=1, DATP split semantics, control-repo origin) clean per-client calibration/test
score artifacts. Provides one CP1-faithful retrain to regenerate clean artifacts.

## 2. Pre-start audit
Read the CP2-T007 verdict and `docs/DATP_CP_Roadmap.md` §13 FB1. Confirm the trigger
is genuinely met and recorded in `CP2_DECISION_LOG.md`. Do not retrain otherwise.

## 3. Scope (only if triggered)
- One retrain: **E=1**, `rounds_initial=40`, `rounds_max=150`, DATP convergence
  criterion, FedAvg weighted by local benign size, Flower.
- Write fresh score artifacts with a complete provenance manifest.
- No hyperparameter re-tuning.

## 4. Non-goals
- No journal artifacts; no E=5; no architecture changes; no per-baseline retraining.
- Do not run if the trigger is not met.

## 5. Scientific locks
E=1 only; clean artifacts shared across B1/B2/B4; train-once derive-many;
determinism (`training_seed=[0..4]`). Heavy training requires explicit authorization
(experiment-gate); GPU path may apply.

## 6. Coding locks
Reuse existing FL training stages; no wrappers; typed config; centralized constants.

## 7. Implementation guidance
Use inherited `src/datp/experiments/stages/train_fl.py` + scoring generation. Write
manifest to `_ai_tracking/manifests/clean_score_artifacts.json`.

## 8. Tests and diagnostics
```text
pytest tests/integration/federated/test_train_once.py -q
pytest tests/integration/scoring/test_score_artifacts.py -q
```

## 9. Graphify
Optional; record deferral.

## 10. Paper-writing notes
Safe wording: "Clean baselines were reproduced under the published DATP conference
protocol; no hyperparameters were re-tuned."

## 11. Acceptance criteria
- Fresh E=1 clean artifacts + manifest exist and pass provenance; CP2-T007 re-passes.

## 12. Blocking conditions
Heavy training without authorization → stop and request authorization via decision
record. Compute/GPU unavailable → record blocker.

## 13. Tracking update
Update Phase-A confirmation #1; log fallback activation in `CP2_DECISION_LOG.md`.

## 14. Completion evidence
New artifacts, manifest, training logs, tests, decision record, progress update.
