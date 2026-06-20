# Rework Decisions

This file records every ambiguity encountered and the chosen resolution.

---

## D-001: B0 centralized baseline disposition

**Ambiguity:** The roadmap does not name a B0/centralized baseline. The existing code
has `Baseline.B0` used as a centralized reference.

**Decision:** Remove `Baseline.B0` from the active ThresholdPolicy enum. It is not
one of the three datp-cp policies. Keep the autoencoder/FedAvg clean training
pipeline code (it supports datp-cp-clean), but remove B0 from any active threshold
comparison workflow.

---

## D-002: Regime A/B/C sweep vs. datp-cp clean pipeline

**Ambiguity:** The old `datp sweep --regime=a` sweep ran B0/B1/B2/B3/B4 across seeds.
The new `make datp-cp-clean` needs to generate clean E=1 N-BaIoT artifacts. The
underlying federated training code is reusable.

**Decision:** Keep `src/datp/federated/`, `src/datp/modeling/`, and the scoring/
calibration pipeline. Remove the `run-regime-a`, `run-regime-b`, `run-regime-c`,
`run-main-matrix`, `sweep-dry-run`, `gate0`-`gate3-code` Makefile targets. Replace
with `datp-cp-clean` which calls the existing clean training/scoring pipeline.

---

## D-003: B3 family threshold removal

**Ambiguity:** `b3_family.py` exists. The roadmap explicitly excludes B3.

**Decision:** Remove `src/datp/thresholding/strategies/b3_family.py` entirely. Remove
`Baseline.B3` from enums. Remove B3 from all tests that relied on it.

---

## D-004: `Baseline` enum vs. `ThresholdPolicy` enum

**Ambiguity:** The codebase has both `Baseline` (B0-B4) and `ThresholdPolicy`
(B1_GLOBAL/B2_PERSONALIZED/B4_CLUSTER). The roadmap only specifies ThresholdPolicy.

**Decision:** Replace `ThresholdPolicy` with new canonical values. The `Baseline`
enum in `core/enums.py` serves the old sweep orchestration and will be removed
(along with old regime/sweep code). Where Baseline is needed for clean training,
keep only Baseline.B1/B2/B4 as internal constants without the B-prefix public API.
Actually, since the clean training pipeline needs to know which threshold style to
use, map directly to ThresholdPolicy. Remove Baseline enum entirely from public API.

---

## D-005: ExperimentStage values — mapping

**Old values:** COMMON, AUDIT_READONLY, NBAIOT_SMOKE, NBAIOT_BOUNDED, NBAIOT_FULL,
CICIOT2023_STRETCH, PAPER_FIGURES

**New values (roadmap):** FINAL_AUDIT, SYNTHETIC_SMOKE, NBAIOT_MAIN,
NBAIOT_FULL_OPTIONAL, STRETCH_DIAGNOSTIC_ONLY

**Decision mapping:**
- AUDIT_READONLY → FINAL_AUDIT
- NBAIOT_SMOKE → SYNTHETIC_SMOKE
- NBAIOT_BOUNDED → NBAIOT_MAIN  
- NBAIOT_FULL → NBAIOT_FULL_OPTIONAL
- CICIOT2023_STRETCH → STRETCH_DIAGNOSTIC_ONLY
- COMMON → remove (not in roadmap, only needed internally)
- PAPER_FIGURES → remove (report is via `datp-cp-report`, not a stage)

---

## D-006: ExperimentScale enum disposition

**Ambiguity:** `ExperimentScale` has SMOKE/BOUNDED/FULL/STRETCH. The roadmap doesn't
have a separate "scale" concept — stages map directly.

**Decision:** Remove `ExperimentScale` enum. Each `ExperimentStage` is self-describing.
The `ExperimentStageConfig.scale` field is removed.

---

## D-007: output root path

**Roadmap:** `outputs/conference_calibration_poisoning/`

**Current code:** `CALIBRATION_POISONING_OUTPUT_ROOT` in `artifacts/constants.py`

**Decision:** Keep existing constant name (it's already domain-named). Verify it
points to `outputs/conference_calibration_poisoning/`. Update if different.

---

## D-008: `datp-cp-clean` Makefile target implementation

**Decision:** `make datp-cp-clean` calls `python -m datp.app.cli clean-run` (new
CLI subcommand) which runs the E=1 FedAvg clean training/scoring pipeline for
N-BaIoT and writes clean artifacts to `outputs/conference_calibration_poisoning/clean/`.

---

## D-009: Old docs/ tickets and tracking files

**Decision:** Do not delete `docs/tickets/` — it contains scientific planning documents.
Remove references to old DATP/CP2 ticket workflow from CLAUDE.md and active docs.
The `docs/DATP_CP_Roadmap.md` is the new source of truth and should be preserved.

---

## D-010: `.claude/agents` and `.claude/skills` — old ticket workflow

**Decision:** Rewrite all `.claude/agents/*.md` and `.claude/skills/*.md` to
reference the new datp-cp roadmap, Makefile targets, and terminology. Remove
ticket-centric language and replace with roadmap-stage and Makefile-command language.
