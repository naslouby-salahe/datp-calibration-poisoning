# CP2 Initial Repository Audit

**Date:** 2026-06-15
**Auditor:** automated agent (read-only inspection)
**Repository:** `/home/naslouby/Projects/datp-calibration-poisoning`
**Purpose:** Pre-ticket-creation audit of the actual repository state for the CP2
(Calibration-Channel Poisoning) conference paper. This audit grounds the ticket
plan under `docs/tickets/`.

> **Evidence rule.** This document records what was inspected on 2026-06-15. It is
> a snapshot, not a contract. Every ticket must re-inspect the actual code, tests,
> configs, manifests, outputs, and `Additional_Docs/` before starting. Do not trust
> this audit or any progress file alone.

---

## 0. Method

- Inspected `src/datp/`, `tests/`, `docs/`, `Additional_Docs/`, `.claude/`,
  `.github/`, `Makefile`, `COMMANDS.md`, `pyproject.toml`, `pyrightconfig.json`,
  `README.md` via directory listings, targeted reads, and exploration subagents.
- Read the central CP2 attack files directly:
  `src/datp/attacks/calibration_poisoning.py`, `poisoning_config.py`.
- Read the CP2 protocol of record: `docs/DATP_CP_Roadmap.md`.

---

## 1. What Already Exists

### 1.1 CP2 attack code (prototype)
- `src/datp/attacks/calibration_poisoning.py` — `PoisoningObjective` enum
  (`RAISE_THRESHOLD`, `LOWER_THRESHOLD`) and `poison_calibration_errors()`.
- `src/datp/attacks/poisoning_config.py` — `CalibrationPoisoningConfig`
  (`attack_rate`, `objective`, `shift_magnitude`, `seed`).
- `src/datp/attacks/poisoning_metrics.py` — `PoisoningEffect`,
  `PoisoningExperimentResult`.
- `src/datp/experiments/calibration_poisoning.py` — `run_poisoning_experiment()`
  comparing B1/B2/B4 under clean vs poisoned calibration.
- Tests: `tests/unit/attacks/` (3 files), `tests/integration/attacks/test_poisoning_experiment.py`.

### 1.2 DATP infrastructure (inherited, broadly reusable)
- **Thresholding** `src/datp/thresholding/` — B1/B2/B3/B4 strategies complete.
  B4 fingerprint locked `("mean","std","skew","p95")`; k-means via sklearn;
  eligibility + Calibration-Pending fallback (`tau_global`) implemented.
- **Scoring** `src/datp/scoring/` — shared per-client score artifacts
  (no baseline subdirectory); `SCORE_COLUMN = "reconstruction_error"`;
  cal / test_benign / test_attack splits separated.
- **Statistics** `src/datp/statistics/` — `bootstrap_ci` (percentile) + `bca_ci`,
  `cv`, `wilcoxon_test` + `bonferroni_correct`, `spearman`, `effect_size`.
- **Validation** `src/datp/validation/` — shared-training invariants, dataset
  schema checks, CICIoT2023 homogeneity gating, recomputation checks.
- **Reporting** `src/datp/reporting/` — figures, tables, bootstrap payloads,
  sidecar provenance.
- **Core enums** `src/datp/core/enums.py` — `Baseline {B0..B4}`, `Regime {A,B,C}`,
  `ClientStatus`, `ThresholdAggregationMethod`, `ThresholdSource`, `MetricName`
  (incl. `CV_FPR`), centralized canonical maps. **Seeds** in `core/seeds.py` use
  `np.random.default_rng`.
- **CLI** `src/datp/app/cli/` — Typer app: `config preview`, `audit results`,
  `checkpoint-protocol`, `report {stats|validate|figures|tables|all}`, `sweep`,
  `status`. Entry point `datp = "datp.cli:cli_entry"`.
- **Makefile** — gates (`gate0..gate3-code`), `test*`, `typecheck`, `lint`,
  `diagnostic-*`, `run-regime-*`, `build-*`, `status`, `audit-results`. Console
  logs auto-captured under `outputs/console_logs/`.

---

## 2. What Appears Reusable

- Thresholding B1/B2/B4 derivation, eligibility, Calibration-Pending fallback.
- Shared scoring artifacts and `ScoreProvider` loading (calibration scores exist).
- Bootstrap (percentile + BCa) and CV machinery for seed-level deltas.
- Core enum/constant centralization pattern and `core/seeds.py` determinism setup.
- Validation invariant + manifest patterns (adaptable to a CP2 manifest).
- Reporting figure/table/sidecar scaffolding.

---

## 3. What Appears Stale or Unsafe (for CP2)

- **CP2 attack prototype does NOT match the protocol.** Current code uses
  `attack_rate` + `shift_magnitude` to *add/subtract a constant* from sampled
  positions. The CP2 protocol (`docs/DATP_CP_Roadmap.md` §6) requires
  `REPLACE_FIXED_BUDGET`: replace `m_i = max(1, round(f·n_i))` positions with
  **values resampled with replacement from a victim-local tail/pool**, holding
  cardinality constant. `shift_magnitude` is a hardcoded scientific knob not in
  the protocol. → **Refactor / replace, do not preserve.**
- **Enum mismatch.** Protocol requires `AttackerObjective {THRESHOLD_RAISE,
  THRESHOLD_LOWER}`, `PoisoningSourceStrategy {RANDOM_BENIGN, HIGH_SCORE_BENIGN,
  LOW_SCORE_BENIGN, LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY}`,
  `CalibrationInjectionRule {REPLACE_FIXED_BUDGET}`, `PoisoningKnowledge`,
  `PoisoningTargetScope`, `PoisoningDefense`, `ExperimentScale`, `AuditDisposition`.
  None of these exist yet. Existing `PoisoningObjective` naming differs.
- **Seed scheme.** No `SeedSequence([training_seed, poisoning_seed, client_id,
  scope_id])` child-seed scheme yet. CP2 forbids integer seed addition.
- **No CP2 manifest / `mu_flag_threshold` lock / provenance gate** (E=1 enforcement)
  exists for CP2 runs.
- **ThresholdPolicy default enum** for CP2 must be `{B1_GLOBAL, B2_PERSONALIZED,
  B4_CLUSTER}` with **B3 excluded**. Inherited `Baseline` correctly keeps B3 for
  DATP but CP2's default policy set must not include B3.

---

## 4. What Appears Journal-Contaminated

- No journal-only code paths detected in CP2-relevant modules. No `Edge-IIoTset`,
  `FedProx`, `Ditto`, `Laridi`, or `E=5` hardcoding found in source.
- `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md` is explicitly
  **ARCHIVED / not operational**. Use as a **contamination boundary only**; do not
  import journal scope into CP2.
- `CICIoT2023` exists as Regime B (external validation) in DATP. For CP2 it is
  **optional stretch only, FB4-gated**. `Edge-IIoTset` is **forbidden** in CP2.

---

## 5. What Needs Refactor

- Replace the CP2 attack prototype with a protocol-faithful injector +
  victim-local reservoir + source strategies.
- Introduce CP2 enums, typed config schema, centralized constants/path registry,
  manifest schema, and the `SeedSequence` child-seed scheme.
- Centralize CP2 scientific constants (fractions, seeds, `n_min=100`, B4 K=3,
  `random_state=42`, `n_init=10`, `max_iter=300`, materiality `δ_τ,i`,
  `mu_flag_threshold`).
- Add CP2 provenance/E=1 gate to manifest validation.

---

## 6. What Tests Already Exist

- `tests/unit/attacks/` — `test_calibration_poisoning.py`, `test_poisoning_config.py`,
  `test_poisoning_metrics.py` (target the prototype; will need rewrite).
- `tests/unit/thresholding/`, `tests/unit/scoring/`, `tests/unit/statistics/`,
  `tests/unit/validation/` — broad DATP coverage reusable as reference.
- `tests/integration/attacks/test_poisoning_experiment.py`.
- `tests/e2e/regime_{a,b,c}/`. No `xfail`/`skip`-masked failures detected; data-
  dependent tests skip gracefully when raw data is absent.

---

## 7. What Commands Exist

- `make test | test-unit | test-integration | test-e2e`
- `make typecheck` (pyright scoped to `baselines` + `evaluation` only) / `make lint` (ruff)
- `make gate0..gate3-code`, `make gates`
- `make diagnostic-*`, `make run-regime-*`, `make sweep-dry-run`, `make status`,
  `make audit-results`, `make build-*`
- CLI: `python -m datp.app.cli ...` / `datp ...` (see `COMMANDS.md`).

---

## 8. Graphify

> **Historical note (audit recorded pre-installation):** At the time this audit
> was written, Graphify was not yet installed. CP2-T004 subsequently completed
> installation (graphifyy==0.8.39, 2026-06-15). The current state is AVAILABLE.
> See `_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`.

- **Graphify is AVAILABLE** — graphifyy==0.8.39 installed via CP2-T004.
  Initial graph: 6229 nodes, 15572 edges, 406 communities.
  Canonical invocation: `graphify update .` (no API key needed).
- Status tracked in `docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`.

---

## 9. .claude / skills / .github State

- `.claude/` — 13 DATP-specific agents, 16 skills, `settings.json`
  (`model: claude-sonnet-4-6`), `settings.local.json` (telegram). Agents/skills are
  DATP/CP2-aligned, not generic; mostly safe to keep. Needs a light CP2-alignment
  pass (CP2 locks, ticket workflow, no-backward-compat, Graphify rule).
- `.github/` — only `copilot-instructions.md`. **No** `workflows/`,
  **no** `pull_request_template`, **no** `ISSUE_TEMPLATE/`. copilot-instructions
  references a `docs/tickets/` ledger that did not previously exist (this plan
  creates it) and a `docs/journal/` package (journal-scope — keep out of CP2).
- No root-level `skills/`, `*.instructions.md`, or `*.prompt.md` files.

---

## 10. Additional_Docs Confirmed

- `Additional_Docs/paper/DATP.pdf` ✅ (conference DATP anchor)
- `Additional_Docs/Synthesis/Claims.md` ✅
- `Additional_Docs/Synthesis/Gap & Limitation Ledger.md` ✅
- `Additional_Docs/Synthesis/Literature Matrix.md` ✅
- `Additional_Docs/Synthesis/State_of_the_Art.md` ✅
- `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md` ✅ (archived; boundary only)
- `docs/DATP_CP_Roadmap.md` ✅ (CP2 protocol of record)

---

## 11. Assumptions Still Unknown (resolve in Phase A)

- Whether persisted clean N-BaIoT score artifacts exist on disk and were produced
  under **E=1** (else FB1 retrain). Provenance/manifest not yet confirmed.
- Whether B4 clean per-seed assignments/effective thresholds are reproducible
  (FB3 gate) and whether B4 K is held at 3 for N-BaIoT in inherited code.
- Which bootstrap variant DATP used for the conference CI (percentile vs BCa) —
  needs to be located and inherited; else default percentile.
- Exact DATP calibration/test chronological split semantics and whether the
  artifacts expose victim-local benign calibration-*candidate* scores not used to
  fit the clean threshold (source-precedence rule §6).
- `M_clean` (clean B1 eligible-client mean FPR) for locking
  `mu_flag_threshold = round(M_clean/8, 2 s.f.)` before any poisoned run.

---

## 12. Conclusion

The repository provides a strong, reusable DATP substrate (thresholding, scoring,
statistics, validation, reporting, enums, CLI). CP2 attack code exists only as a
**non-protocol prototype** and must be rebuilt to the `docs/DATP_CP_Roadmap.md`
contract. No journal contamination is present in code. Graphify has since been
installed (CP2-T004; see `_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`).
The ticket plan proceeds: setup → read-only audit → protocol lock → core
implementation → smoke → MVP → optional full → final experiment/analysis/paper,
with periodic refactor and scientific-drift tickets and conditional fallbacks.

---

## 13. Phase 00 Refresh Addendum

**Date:** 2026-06-15
**Ticket:** CP2-T001

Phase 00 re-inspected the current repository state and found the core audit still
substantively current.

Refresh evidence:

- `find src/datp tests -maxdepth 3 -type f | sort`
- `make help`
- targeted `rg` scans for `shift_magnitude`, CP2 attack prototype symbols,
  thresholding/scoring/statistics anchors, Graphify, and forbidden-scope terms
- `graphify update .`

Current attack inventory remains:

- `src/datp/attacks/calibration_poisoning.py`
- `src/datp/attacks/poisoning_config.py`
- `src/datp/attacks/poisoning_metrics.py`
- `src/datp/experiments/calibration_poisoning.py`

The attack prototype still uses `attack_rate` and `shift_magnitude`; this remains
non-protocol and is scheduled for later audit/replacement. No Phase 00 production
code changes were made.

Graphify refresh: `graphify update .` completed during Phase 00. Latest graph
after sidecar cleanup: 6331 nodes, 15668 edges, and 397 communities. See
`docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`.
