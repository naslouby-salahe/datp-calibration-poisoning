# CP2 Ticket Index

Authoritative list of all CP2 tickets. `R` = refactor checkpoint, `D` = scientific
drift check. Graphify (`Gfy`) and paper-notes (`PN`) columns: `Y`/`N`/`C` (conditional).
Track current status in `_ai_tracking/progress/CP2_PROGRESS.md` and the individual
ticket headers.

> Do not trust this index or the progress file alone — inspect the repository.

**Audit reconciliation (2026-06-16).** A full Phase 00–D code-backed re-audit
confirmed the implementation matches the tracking log and corrected stale ticket
headers (which still read `not started`). Verified status:
> - **Phase 00 (T000–T006):** `done` — setup/audit deliverables present.
> - **Phase A (T007–T015):** `done` — audit reports in `_ai_tracking/audits/`.
>   **CP2-FB1:** `blocked` (TRIGGERED by T007: clean artifacts absent + `config.yaml`
>   `local_epochs: 5`; execution needs E=1 fix + retraining authorization).
>   **CP2-FB3:** conditional, **not triggered** (B4 reproducible).
> - **Phase B (T016–T023):** `done` — enums/config/constants/manifest/seeds/guardrails
>   implemented and tested.
> - **Phase C (T024–T037):** `done` — injector, reservoir, sources, B1/B2/B4
>   recompute, metrics, diagnostics, inference implemented and tested.
>   **CP2-FB2:** conditional, **not triggered** (degenerate-tail handling preventively
>   built into `reservoir.py`).
> - **Phase D (T038–T041):** `done` — smoke harness + 15 invariants pass.
>
> Evidence: 1003 CP2 tests pass; `ruff`/`pyright` clean on the CP2 surface; no source
> drift.
>
> **Phase E entry gate (2026-06-16): superseded — FB1 executed, Phase E complete.**
> CP2-T042 originally found FB1 triggered (no real artifacts, `config.yaml`
> `local_epochs: 5`); the user explicitly authorized the FB1 heavy retrain the same
> day. `local_epochs` was fixed to `1` and one E=1 federated retrain executed
> (`datp sweep --regime a ...`, 25/25 cells, ~70 min, GPU), producing real N-BaIoT
> clean score artifacts for all 5 training seeds (FB1 status: **closed**). Phase E
> then ran to completion: CP2-T043/T044 diagnostics, the CP2-T044-authorized bounded
> MVP run (CP2-T045, real execution, 1620-cell `nbaiot_mvp_manifest.json`), CP2-T046
> (manifest audit, PASS), CP2-T047 (kill-trigger evaluation, NO KILL TRIGGER FIRES),
> CP2-T048 (drift check, PASS) — all `done`. CP2-T049 (continue/stop/pivot decision)
> recorded **CONTINUE**; see `_ai_tracking/decisions/CP2_DECISION_LOG.md`
> (`CP2-T049` entry) for full rationale and the one open evidentiary caveat (RAISE
> victim ΔTPR not yet computed). **Phase F tickets are now open for implementation
> work; actual Phase F/G experiment execution remains separately gated at CP2-T056**
> per CLAUDE.md §2.8. See `_ai_tracking/diagnostics/CP2-T042_nbaiot_load_dryrun.md`,
> `_ai_tracking/run_logs/CP2_PHASE_E_ENTRY_GATE.md`,
> `_ai_tracking/decisions/CP2_FALLBACK_REGISTER.md`, and `CP2_PROGRESS.md`.

---

## Phase 00 — Setup (`phase_00_setup/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T000 | phase_00_setup/CP2-T000.md | audit | critical | — | T001 | Ticket system bootstrap | static | C | N |
| CP2-T001 | phase_00_setup/CP2-T001.md | audit | critical | T000 | T007 | Initial repository audit | static | C | N |
| CP2-T002 | phase_00_setup/CP2-T002.md | audit | high | T001 | T009 | Additional_Docs alignment audit | static | C | Y |
| CP2-T003 | phase_00_setup/CP2-T003.md | audit | high | T001 | — | .claude / skills / .github audit & update | static | C | N |
| CP2-T004 | phase_00_setup/CP2-T004.md | audit | high | T001 | all | Graphify discovery & workflow doc | static, graphify | Y | N |
| CP2-T005 | phase_00_setup/CP2-T005.md | refactor | medium | T000-T004 | — | [R] setup/tracking/agent-config consistency | static, graphify | Y | N |
| CP2-T006 | phase_00_setup/CP2-T006.md | scientific-drift | high | T002,T005 | T007 | [D] setup & planning scope drift check | static | C | Y |

## Phase A — Read-only audit (`phase_a_audit/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T007 | phase_a_audit/CP2-T007.md | audit | critical | T001,T006 | T015,FB1 | Clean score artifact discovery, provenance & E=1 audit | static | C | Y |
| CP2-T008 | phase_a_audit/CP2-T008.md | audit | high | T007 | T015 | DATP split semantics audit | static | C | Y |
| CP2-T009 | phase_a_audit/CP2-T009.md | audit | critical | T002 | T015 | Journal-contamination & forbidden-scope audit | static | C | Y |
| CP2-T010 | phase_a_audit/CP2-T010.md | audit | high | T001 | T016,T027 | Existing CP2 attack-code audit | static | C | N |
| CP2-T011 | phase_a_audit/CP2-T011.md | audit | critical | T001 | T015,T031,FB3 | Thresholding & B4 procedure audit | static | C | Y |
| CP2-T012 | phase_a_audit/CP2-T012.md | audit | high | T001 | T033,T035 | Scoring/statistics/reporting reuse audit | static | C | Y |
| CP2-T013 | phase_a_audit/CP2-T013.md | refactor | medium | T007-T012 | — | [R] audit-phase cleanup checkpoint | static, graphify | Y | N |
| CP2-T014 | phase_a_audit/CP2-T014.md | scientific-drift | high | T009,T011 | T015 | [D] audit-phase drift check | static | C | Y |
| CP2-T015 | phase_a_audit/CP2-T015.md | audit | critical | T007,T008,T011,T014 | T016 | Phase-A gate report | static | C | Y |
| CP2-FB1 | phase_a_audit/CP2-FB1.md | scientific-drift | critical | T007 | — | (cond) clean artifacts fail provenance | integration, e2e | C | Y |
| CP2-FB3 | phase_a_audit/CP2-FB3.md | scientific-drift | high | T011 | — | (cond) B4 not reproducible | unit, integration | C | Y |

## Phase B — Protocol lock (`phase_b_protocol_lock/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T016 | phase_b_protocol_lock/CP2-T016.md | implementation | critical | T010,T015 | T017,T027 | CP2 enum definitions | unit, static | Y | N |
| CP2-T017 | phase_b_protocol_lock/CP2-T017.md | implementation | critical | T016 | T021,T028 | CP2 typed config schema | unit, static | Y | N |
| CP2-T018 | phase_b_protocol_lock/CP2-T018.md | implementation | high | T016 | T044 | CP2 constants & path registry | unit, static | Y | N |
| CP2-T019 | phase_b_protocol_lock/CP2-T019.md | implementation | critical | T016,T017 | T035,T044 | Manifest schema & seed child-generation design | unit, static | Y | N |
| CP2-T020 | phase_b_protocol_lock/CP2-T020.md | refactor | medium | T016-T019 | — | [R] enums/config/constants consolidation | unit, static, graphify | Y | N |
| CP2-T021 | phase_b_protocol_lock/CP2-T021.md | implementation | high | T017,T019 | T028 | Artifact validation & provenance-gate design | unit, static | Y | N |
| CP2-T022 | phase_b_protocol_lock/CP2-T022.md | implementation | high | T017 | T028 | Scientific guardrails & CLI stage layout | unit, static | Y | N |
| CP2-T023 | phase_b_protocol_lock/CP2-T023.md | scientific-drift | high | T016,T020 | T024 | [D] protocol-lock drift check | unit, static | C | Y |

## Phase C — Core implementation (`phase_c_core_implementation/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T024 | phase_c_core_implementation/CP2-T024.md | implementation | high | T023 | T038 | Synthetic score fixtures | unit | C | N |
| CP2-T025 | phase_c_core_implementation/CP2-T025.md | implementation | high | T017,T024 | T027 | Score containers & eligibility model | unit, static | Y | N |
| CP2-T026 | phase_c_core_implementation/CP2-T026.md | implementation | high | T025 | T027 | Victim-local reservoir selection | unit, static | Y | Y |
| CP2-T027 | phase_c_core_implementation/CP2-T027.md | implementation | critical | T016,T026 | T029,T038 | Fixed-budget replacement injector | unit, static | Y | Y |
| CP2-T028 | phase_c_core_implementation/CP2-T028.md | refactor | medium | T025-T027 | — | [R] injector/reservoir cleanup | unit, static, graphify | Y | N |
| CP2-T029 | phase_c_core_implementation/CP2-T029.md | implementation | high | T027 | T038 | Source strategies (RANDOM/HIGH/LOW) | unit, static | Y | Y |
| CP2-T030 | phase_c_core_implementation/CP2-T030.md | implementation | high | T025 | T033 | B1/B2 threshold recomputation | unit, static | Y | N |
| CP2-T031 | phase_c_core_implementation/CP2-T031.md | implementation | critical | T011,T030 | T033 | B4 recomputation & client-indexed decomposition | unit, static | Y | Y |
| CP2-T032 | phase_c_core_implementation/CP2-T032.md | scientific-drift | high | T027,T031 | — | [D] attack & thresholding drift check | unit, static | C | Y |
| CP2-T033 | phase_c_core_implementation/CP2-T033.md | implementation | critical | T012,T030,T031 | T035 | Metric engine (Δτ, CV(FPR), coverage) | unit, static | Y | Y |
| CP2-T034 | phase_c_core_implementation/CP2-T034.md | implementation | high | T033 | T035 | ASR, blast radius & spillover diagnostics | unit, static | Y | Y |
| CP2-T035 | phase_c_core_implementation/CP2-T035.md | implementation | critical | T019,T033,T034 | T038 | Paired comparison, bootstrap/sign-test, manifest & run logging | unit, integration, static | Y | Y |
| CP2-T036 | phase_c_core_implementation/CP2-T036.md | refactor | medium | T029-T035 | — | [R] core-implementation consolidation | unit, integration, static, graphify | Y | N |
| CP2-T037 | phase_c_core_implementation/CP2-T037.md | scientific-drift | critical | T035,T036 | T038 | [D] core-implementation drift check | unit, integration, static | C | Y |
| CP2-FB2 | phase_c_core_implementation/CP2-FB2.md | implementation | medium | T026 | — | (cond) degenerate tail reservoir | unit | C | Y |

## Phase D — Smoke & diagnostics (`phase_d_smoke_validation/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T038 | phase_d_smoke_validation/CP2-T038.md | diagnostic | critical | T024,T027,T029,T031,T035,T037 | T039 | Synthetic smoke harness & invariants 1–6 | unit, diagnostic | Y | N |
| CP2-T039 | phase_d_smoke_validation/CP2-T039.md | diagnostic | critical | T038 | T042 | Smoke invariants 7–11 | unit, diagnostic | Y | N |
| CP2-T040 | phase_d_smoke_validation/CP2-T040.md | refactor | medium | T038,T039 | — | [R] smoke & test consolidation | unit, integration, static, graphify | Y | N |
| CP2-T041 | phase_d_smoke_validation/CP2-T041.md | scientific-drift | high | T039 | T042 | [D] smoke-validation drift check | unit, diagnostic | C | Y |

## Phase E — MVP (`phase_e_mvp/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T042 | phase_e_mvp/CP2-T042.md | diagnostic | high | T039,T015 | T043 | N-BaIoT artifact loading dry-run | integration, diagnostic | C | Y |
| CP2-T043 | phase_e_mvp/CP2-T043.md | diagnostic | high | T042 | T044 | One-seed/one-victim & one-seed/all-victims diagnostics | integration, diagnostic | C | Y |
| CP2-T044 | phase_e_mvp/CP2-T044.md | diagnostic | high | T043,T018,T019 | T046 | All-seeds/one-victim diagnostic & MVP run plan | integration, diagnostic | C | Y |
| CP2-T045 | phase_e_mvp/CP2-T045.md | refactor | medium | T042-T044 | — | [R] MVP-prep cleanup | unit, integration, static, graphify | Y | N |
| CP2-T046 | phase_e_mvp/CP2-T046.md | audit | high | T044 | T047 | MVP manifest & result-sanity audit | integration | C | Y |
| CP2-T047 | phase_e_mvp/CP2-T047.md | audit | critical | T046 | T049 | Kill-trigger evaluation | static | C | Y |
| CP2-T048 | phase_e_mvp/CP2-T048.md | scientific-drift | high | T046 | T049 | [D] MVP drift check | static | C | Y |
| CP2-T049 | phase_e_mvp/CP2-T049.md | audit | critical | T047,T048 | T050,T056 | MVP continue/stop/pivot decision | static | C | Y |

## Phase F — Optional full (`phase_f_full_optional/`) — OPEN (CP2-T049: CONTINUE, 2026-06-16); execution still gated at CP2-T056

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T050 | phase_f_full_optional/CP2-T050.md | experiment | medium | T049 | — | (cond) add fraction 0.05 | integration, diagnostic | C | Y |
| CP2-T051 | phase_f_full_optional/CP2-T051.md | implementation | medium | T049 | — | (cond) multi-client pairs & 20 triples, independent streams | unit, integration | Y | Y |
| CP2-T052 | phase_f_full_optional/CP2-T052.md | implementation | medium | T049 | T053 | (cond) trimmed-calibration defense | unit, integration | Y | Y |
| CP2-T053 | phase_f_full_optional/CP2-T053.md | audit | medium | T052 | — | (cond) defense regression & recovery audit | integration | C | Y |
| CP2-T054 | phase_f_full_optional/CP2-T054.md | audit | low | T049 | FB4 | (cond) CICIoT2023 stretch pre-audit | static | C | Y |
| CP2-T055 | phase_f_full_optional/CP2-T055.md | scientific-drift | high | T050-T054 | — | (cond) [D] full-scope drift check | integration, static | C | Y |
| CP2-FB4 | phase_f_full_optional/CP2-FB4.md | scientific-drift | medium | T054 | — | (cond) CICIoT2023 unsafe / B4 K shifts | static | C | Y |

## Phase G — Experiment, analysis & paper (`phase_g_experiment_and_paper/`)

| ID | File | Type | Pri | Deps | Blocks | Purpose | Tests | Gfy | PN |
|---|---|---|---|---|---|---|---|---|---|
| CP2-T056 | phase_g_experiment_and_paper/CP2-T056.md | experiment | critical | T049 | T057 | Run final CP2 experiments | integration, e2e | C | Y |
| CP2-T057 | phase_g_experiment_and_paper/CP2-T057.md | analysis | critical | T056 | T058 | Build final analysis & figures | integration | C | Y |
| CP2-T058 | phase_g_experiment_and_paper/CP2-T058.md | paper | critical | T057 | — | Write paper package & claim audit | static | C | Y |

---

## Counts

- Numbered tickets: **59** (CP2-T000 … CP2-T058).
- Fallback tickets: **4** (CP2-FB1, FB2, FB3, FB4) — conditional.
- Refactor checkpoints: CP2-T005, T013, T020, T028, T036, T040, T045.
- Scientific-drift checks: CP2-T006, T014, T023, T032, T037, T041, T048, T055 (+ fallbacks FB1, FB3).
- Final three (fixed): CP2-T056 (experiment), CP2-T057 (analysis), CP2-T058 (paper).
