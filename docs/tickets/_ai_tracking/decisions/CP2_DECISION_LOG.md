# CP2 Decision Log

Record blockers, pivots, fallback activations, and hard-stops here. Each entry:
exact blocker / decision, command or action involved, evidence, fallbacks
attempted, remaining safe work, next action.

> No blocker is resolved by prose alone — link to the real evidence path.

---

## Entries

---

## 2026-06-16 | CP2-T007 | FB1 TRIGGERED — Clean score artifacts absent; E=5 config flag

**Ticket:** CP2-T007

**Trigger:** CP2-FB1 trigger condition met. No CP2-controlled clean N-BaIoT
per-client calibration/test score artifacts exist in this repository. `outputs/`
contains only `console_logs/`.

**Evidence:**
- `outputs/` inspection: no `.parquet`, no `scoring_manifest.json`, no model
  checkpoints (2026-06-16 audit).
- `src/datp/conf/config.yaml` line 41: `local_epochs: 5` (E=5, forbidden for CP2).
- Scoring infrastructure (generation, validation, manifest) is present and correct.
- Evidence files: `_ai_tracking/audits/CP2-T007_artifact_audit.md`,
  `_ai_tracking/manifests/clean_score_artifacts.json`.

**Additional finding:** `local_epochs: 5` in `src/datp/conf/config.yaml` was missed
by the T001 scan because the rg pattern `epochs *= *5` requires `=`, but YAML
uses `:`. If training were run now, artifacts would be E=5 (rejected).

**Fallback attempted:** CP2-FB1 triggered but **NOT YET EXECUTED**.

**FB1 execution blocked by:** Phase A is read-only. Additionally, `local_epochs: 5`
must be corrected to `local_epochs: 1` before FB1 can produce valid E=1 artifacts.

**Remaining safe Phase-A work:** All other Phase-A tickets (T008–T015) are
independent of artifact existence for the code audit. They proceed as read-only.

**Next action:**
1. Phase B (T017/T022): fix `local_epochs: 1` and add FederationConfig validator.
2. After Phase B config lock: activate FB1 with explicit authorization (retraining
   authorization required per FB1 §12).
3. Phase-A confirmation #1 remains PENDING until FB1 completes.

---

## 2026-06-16 | CP2-T038/T039 | Two divergent "11 smoke invariants" lists reconciled by asserting the union

**Ticket:** CP2-T038, CP2-T039 (Phase D entry)

**Decision:** The Phase D agent prompt / ticket text (CP2-T038 §3, CP2-T039 §3) and
the protocol-of-record `docs/DATP_CP_Roadmap.md` §10 line 142 each enumerate "11
smoke invariants", but the two lists are **not identical**. Per CLAUDE.md
source-of-truth hierarchy the roadmap outranks the ticket index, and CP2-T041 §2
explicitly audits invariants against roadmap §11. To satisfy both authorities the
smoke harness asserts the **union** of both lists, not just the prompt's 11.

**Prompt/ticket list (1–11):** f=0→zero Δτ; cardinality preserved; no in-place
mutation; HIGH raises / LOW lowers; Calibration-Pending excluded + gets tau_global;
determinism; B4 Δτ_total=Δτ_agg+Δτ_churn; two-layer stats (bootstrap on 5 seed
aggregates, not 45); manifest round-trip (child seeds, locks, reservoir mode,
mu_flag); AUROC invariant; CV(FPR) with coverage and no ε.

**Roadmap §10 list (1–11) adds these not in the prompt list:** RANDOM_BENIGN →
near-null (negative control); B1 victim shift < B2 victim shift under the same
single-client attack; B4 K stays fixed at 3 under clean **and** poisoned cal
(never silently data-adaptive); outputs written to temp only.
(Roadmap's "B4 decomposition computable & finite" maps to prompt invariant 7;
"clean arrays never mutated" and "reproducibility" overlap prompt 3 and 6.)

**Evidence:** `docs/DATP_CP_Roadmap.md:142`; `docs/tickets/phase_d_smoke_validation/
CP2-T038.md:24-32`, `CP2-T039.md:21-29`, `CP2-T041.md:18-20`.

**Action:** harness (`src/datp/testsupport/cp2_smoke_harness.py`) +
`tests/integration/attacks/test_cp2_smoke.py` assert all distinct invariants from
both lists. CP2-T041 drift report cross-checks the union against roadmap §11.

**Next action:** implement harness + invariant tests (CP2-T038/T039).

---

## 2026-06-16 | CP2-T038 | Undeclared `statsmodels` dependency broke `inference.py` import (progress-log contradiction)

**Ticket:** CP2-T038 (surfaced while wiring the smoke harness)

**Trigger:** `tests/integration/attacks/test_cp2_smoke.py` failed to collect with
`ModuleNotFoundError: No module named 'statsmodels'`. Root cause:
`src/datp/attacks/inference.py:25` imports `statsmodels.stats.multitest.multipletests`
at module top level, but `statsmodels` was **not** installed in `.venv` and **not**
declared in `pyproject.toml` `[project].dependencies`.

**Repository-reality contradiction (CLAUDE.md §1):** `CP2_PROGRESS.md` records
"CP2-T035 … 54 inference tests pass" and the T037 drift report records 282 attacks
tests passing. With the current environment `tests/unit/attacks/test_inference.py`
does **not** collect at all (`pytest --collect-only` errors). Repository reality
wins: those counts were only achievable in an environment where statsmodels was
present, but the dependency was never tracked, so the green state was not
reproducible. Recorded here per the evidence rule.

**Fix:** (1) `uv pip install statsmodels` → statsmodels 0.14.6 + patsy 1.0.2 installed
in `.venv`. (2) Added `"statsmodels"` to `pyproject.toml` dependencies (between
`scipy` and `structlog`) so the dependency is declared and reproducible. No logic
change to `inference.py`; Holm remains descriptive-only and gated behind
`include_holm=False`.

**Evidence:**
- `src/datp/attacks/inference.py:25` (top-level import).
- `pyproject.toml` dependencies (statsmodels now declared).
- After fix: `pytest tests/unit/attacks tests/integration/attacks` → 301 passed.

**Remaining safe work:** none blocked. Two-layer bootstrap (the inferential core)
depends only on `scipy`/numpy via `datp.statistics.bootstrap`; statsmodels is used
solely for the descriptive Holm correction.

**Next action:** CP2-T040 consolidation/skip audit; CP2-T041 drift gate.
