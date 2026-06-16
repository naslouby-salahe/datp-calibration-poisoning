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

---

## 2026-06-16 | CP2-T042 | FB1 RE-CONFIRMED at Phase E gate — MVP blocked (hard-stop)

**Ticket:** CP2-T042 (Phase E entry — real N-BaIoT artifact load dry-run)

**Decision/blocker:** Phase E MVP cannot start. The CP2-T042 read-only,
provenance-gated load of real N-BaIoT clean scores fails at the entry gate. This
re-confirms FB1 (originally triggered at CP2-T007) at the Phase E boundary and routes
Phase E to a hard-stop. **No experiment, training, scoring, config change, or
`outputs/` write was performed.**

**Phase E entry-gate result:**
- (1) CP2-T041 drift report exists — PASS.
- (2) Synthetic smoke invariants pass — PASS (15 asserted+passing).
- (3) No unresolved Phase-D blockers — **FAIL** (FB1 triggered & unexecuted).
- (4) Real-data load still provenance-gated — PASS.
Gate **NOT SATISFIED** on requirement (3).

**Evidence (real repository state, re-inspected — not trusting prior logs):**
- `find outputs -type f` → 2 files only: `console_logs/…__help.log`, `logs/datp.log`.
  No `.parquet`, no scoring manifest, no checkpoint, no
  `outputs/conference_calibration_poisoning/`.
- `rg -n "local_epochs" src/datp/conf/config.yaml` → `41:  local_epochs: 5` (**E=5**).
- `_ai_tracking/manifests/clean_score_artifacts.json` → `"verdict":
  "ARTIFACTS_MISSING"`, `"e5_in_yaml_config": true`.
- Diagnostic report: `_ai_tracking/diagnostics/CP2-T042_nbaiot_load_dryrun.md`.
- Run log: `_ai_tracking/run_logs/CP2_PHASE_E_ENTRY_GATE.md`.
- Fallback register: `_ai_tracking/decisions/CP2_FALLBACK_REGISTER.md`.

**Two simultaneous failure modes (per CP2-T042 §12):** (a) MISSING — no clean
artifacts to load; (b) E=5 — config would produce gate-rejected artifacts.
Consequently `mu_flag_threshold` (required locked from clean B1 eligible-client mean
FPR **before** any poisoned run) cannot be locked, and the bounded MVP run plan
(CP2-T044) cannot be produced.

**Fallback attempted:** none executed. FB1 remains TRIGGERED — awaiting
authorization. Editing `local_epochs 5→1` (scientific-meaning change) and running the
FB1 retrain (heavy federated training, 40–150 rounds × 5 seeds) both require explicit
authorization per FB1 §5/§12 and CLAUDE.md §9 hard-stop rules. The Phase E agent
prompt authorizes the MVP **analysis matrix** but does **not** authorize FB1
retraining or the config-semantics change.

**Remaining safe work:** none within Phase E until E=1 clean artifacts exist. All
Phase A–D code/audits remain valid and unchanged.

**Next action:** Obtain an explicit human decision on FB1:
1. **AUTHORIZE FB1** — fix config to E=1 and run the one retrain + scoring, then
   resume CP2-T042→T049; or
2. **HOLD** — leave Phase E blocked and stop.
Confirm compute/GPU availability before authorizing (FB1 §12).

---

## 2026-06-16 | CP2-T043–T049 | BLOCKED (transitive on FB1)

**Tickets:** CP2-T043, CP2-T044, bounded MVP run (T044→T046 bridge), CP2-T045,
CP2-T046, CP2-T047, CP2-T048, CP2-T049.

**Status:** Not started — blocked transitively by the FB1 hard-stop above. Each
depends, directly or via the missing MVP result artifacts, on real E=1 N-BaIoT clean
scores that do not exist. No kill-trigger, drift, or continue/stop/pivot decision can
be made on absent evidence. CP2-T049 records **no** decision (CONTINUE/STOP/PIVOT
would all be unevidenced). Phase F stays closed; Phase G path undetermined pending FB1.

---

## 2026-06-16 | FB1 | AUTHORIZED by human — executing E=1 retrain

**Decision:** The user (Salaheddine Naslouby) explicitly authorized FB1 execution
(config fix + one federated retrain) when asked directly whether to authorize, hold,
or check compute first. Chose **"Authorize FB1 now."**

**Pre-flight checks performed before executing:**
- GPU confirmed available and idle: NVIDIA RTX 5060 Ti, 16 GB, 0 other processes
  (`nvidia-smi`); `torch.cuda.is_available()` → `True`.
- N-BaIoT raw data confirmed present: `data/raw -> /home/naslouby/Projects/datp-shared-data/raw`,
  9 device directories present under `N-BaIoT/`.
- Entrypoint confirmed: `datp sweep --regime a --base-dir outputs --data-root .`
  (existing, tested DATP pipeline — `tests/integration/federated/test_train_once.py`
  exercises the same train→score path). No new wrapper/script written, per FB1 §6
  "reuse existing FL training stages; no wrappers."
- `REGIME_BASELINES[Regime.A]` = {B0, B1, B2, B3, B4}; Regime A has no `alpha` axis;
  no `checkpoint_protocol` configured in `config.yaml` (single-pass per cell, no
  milestone multiplier). 5 seeds × 5 baselines = 25 cells, but only 5 unique shared
  FL trainings (B1–B4 share one training per seed; B0 is isolated/centralized) +
  5 isolated B0 trainings.

**Action taken:** `src/datp/conf/config.yaml:41` `local_epochs: 5 → 1` (E=1 lock, the
only change — no hyperparameter re-tuning, no architecture change, per FB1 §3/§4).

**Next:** dry-run validation, then launch the real sweep for Regime A only (matches
CP2 dataset lock `REGIME_A_NBAIOT`), training_seed=[0,1,2,3,4], in the background;
monitor to completion; then re-run the CP2-T007/T042 provenance gate against the
freshly generated artifacts.

**Outcome:** FB1 retrain completed cleanly. `datp sweep --regime a` ran 25/25
cells, 0 failed, ~4174.5s (~70 min) on GPU. All 9 N-BaIoT clients eligible
(`n_min=100` satisfied everywhere). Checkpoints + `scoring_manifest.json` +
per-client `cal/test_benign/test_attack` parquets written under
`outputs/checkpoints/a/seed_{0..4}/` and `outputs/scores/a/seed_{0..4}/`;
resolved config confirms `local_epochs: 1` (E=1). FB1 status: **executed**.

---

## 2026-06-16 | GOVERNANCE FIX | CP2-T056 hard-stop does not gate the Phase E bounded MVP

**Trigger:** Before writing any real-data MVP runner, found that
`src/datp/config/stages.py` (`Cp2Stage.NBAIOT_SMOKE` and `Cp2Stage.NBAIOT_MVP`)
both had `gate="CP2-T056"`, and CLAUDE.md's Hard Stop Rules (§9) and Ticket
Workflow (§2.8) literally said "an experiment would run before CP2-T056
authorization" / "do not run final experiments before CP2-T056" — which on a
literal reading would also block the Phase E bounded MVP that this agent
prompt explicitly authorizes via CP2-T044. Per CLAUDE.md §9, this is exactly a
"stop and write a decision record" trigger — escalated to the user rather than
self-resolved.

**User decision (explicit):** CP2-T056 is **not** the authorization gate for
the Phase E bounded MVP. CP2-T056 remains the gate for the later final/full
CP2 experiment only. The correct Phase E gate is CP2-T044 (run plan locked +
`mu_flag_threshold` fixed from clean data).

**Reasoning (confirmed against `TICKET_INDEX.md`):** CP2-T056 ("Run final CP2
experiments", `phase_g_experiment_and_paper/CP2-T056.md`) depends on CP2-T049,
which depends on the Phase E MVP results (via T046/T047/T048). CP2-T056 cannot
therefore be a prerequisite for the MVP itself — `MVP → T049 → T056`, not
`T056 → MVP`. The `gate="CP2-T056"` on the SMOKE/MVP stage entries was a stale
Phase-B-era placeholder (written in CP2-T022, before the Phase E ticket plan
T042–T049 existed) and was never mechanically enforced (`allow_run` is a
separate hardcoded `False`, and no execution code path actually reads `gate`).

**Corrections made (all four committed before resuming Phase E execution):**
1. `CLAUDE.md` §2.8 — clarified "final experiments" means the Phase G
   final/full run; the CP2-T044-authorized bounded MVP is explicitly carved
   out as not a violation; full-scope/Phase F/G/pairs-triples/defenses/extra
   datasets remain gated until CP2-T056 (or FB3/FB4).
2. `CLAUDE.md` §9 hard-stop bullet — same clarification, with the explicit
   carve-out for the CP2-T044-authorized bounded MVP.
3. `src/datp/config/stages.py` — `Cp2Stage.NBAIOT_SMOKE.gate`: `"CP2-T056"` →
   `"CP2-T043"` (real-data smoke diagnostics belong to Phase E, not Phase G).
   `Cp2Stage.NBAIOT_MVP.gate`: `"CP2-T056"` → `"CP2-T044"`. Descriptions
   updated to state the CP2-T056-is-not-the-gate reasoning inline.
   `allow_run` left `False` for both (T043/T044 have not yet been completed
   at the time of this fix — flipping `allow_run` is a separate, later step
   once each gate's own acceptance criteria are actually met).
4. `src/datp/app/cli/poison.py` — module docstring and `_PHASE_B_NOTICE` no
   longer hardcode "blocked until CP2-T056"; they now point to each stage's
   own `gate` field (already printed separately by `dry-run`/`smoke`).

**What remains forbidden before CP2-T056 (unchanged):** the Phase G final/full
experiment itself, Phase F/G scaling, expanded seeds, fraction `0.05`,
pair/triple target scopes, defenses, CICIoT2023, Edge-IIoTset, journal scope,
venue strategy, any training/model/aggregation/test-data poisoning, and any
run outside the exact CP2-T044-authorized bounded MVP matrix.

**Verification:** `pytest tests/unit/config/test_stages.py tests/unit/app/cli/test_poison_cli.py`
→ 33 passed; `pyright src/datp/config/stages.py src/datp/app/cli/poison.py` →
0 errors; `ruff check` on both files → clean.

**Next:** resume Phase E at CP2-T042 (real-artifact verification), proceeding
through T043 → T044 (lock the bounded MVP plan + `mu_flag_threshold`) → execute
the bounded MVP matrix → T045–T049.

---

## 2026-06-16 | CP2-T044 | Bounded MVP run plan locked; CP2-T043/T044 gates flipped allow_run=True

CP2-T044 acceptance criteria met: multi-seed stability confirmed (5/5 sign
consistency on all 6 directional policy×source combinations, bounded
magnitude CV 0.08–0.17), `mu_flag_threshold` locked per training seed
(5 distinct values: 0.0050/0.0049/0.0056/0.0053/0.0050), and the exact bounded
MVP matrix locked: 3 policies × 3 sources × 4 fractions × 9 eligible victims
× 5 paired (training_seed, poisoning_seed) = **1620 cells**, `SINGLE_CLIENT`
scope only, `REGIME_A_NBAIOT` only.

**Artifact-strategy decision (resolves a deferred architectural question from
CP2-T042/T043 work):** `Cp2CellId`/`Cp2Layout.cell_paths()` (the full-scope,
Phase-G-gated per-cell directory tree) carries no victim dimension, while the
MVP needs per-victim granularity. Resolution: the bounded MVP does **not**
use the per-cell tree at all. It writes exactly one file at the path
CP2-T018 already locked for this purpose — `Cp2Layout.nbaiot_mvp_manifest()`
→ `nbaiot_mvp_manifest.json` — containing run-level provenance plus a
1620-row results array. No change to `Cp2CellId`/`Cp2Layout` was needed; no
new artifact-name constant was invented. See
`_ai_tracking/run_logs/CP2-T044_mvp_run_plan.md` §3.

**Stage registry update:** per the CP2-T056-vs-CP2-T044 governance fix
(entry above), `allow_run` was deliberately left `False` for
`Cp2Stage.NBAIOT_SMOKE`/`NBAIOT_MVP` pending actual completion of their gates
(CP2-T043/CP2-T044). Both gates are now genuinely satisfied (CP2-T043: done,
diagnostics PASS; CP2-T044: done, this entry). Flipped:
`src/datp/config/stages.py` — `NBAIOT_SMOKE.allow_run` `False→True`,
`NBAIOT_MVP.allow_run` `False→True`. `NBAIOT_FULL` (FB3), `CICIOT2023_STRETCH`
(FB4), `PAPER_FIGURES` (CP2-T057) remain `False` — none of those gates are
satisfied. This is the narrow, per-stage application the registry was
designed for, not a broad loosening (CLAUDE.md hard-stop guard: the allowed
run stays restricted to exactly the CP2-T044 matrix above).

Also fixed a latent CLI staleness bug exposed by this flip:
`app/cli/poison.py` `preview`/`dry-run` printed "Gate X must be resolved
before execution" whenever `cfg.gate` was set, even after that gate became
satisfied (`allow_run=True`). Changed both call sites to
`if cfg.gate and not cfg.allow_run`.

**Files changed:** `src/datp/config/stages.py` (allow_run flips + docstring +
description updates), `src/datp/app/cli/poison.py` (gate-message guard),
`tests/unit/config/test_stages.py` (`test_no_stage_allows_run_in_phase_b` →
`test_only_stages_with_a_completed_gate_allow_run`, now asserts the exact
{NBAIOT_SMOKE, NBAIOT_MVP} runnable set instead of "all False"),
`tests/unit/app/cli/test_poison_cli.py` (split the stale single
nbaiot_mvp-blocked-notice test into a still-blocked-stage check on
`nbaiot_full` plus a new no-longer-blocked check on `nbaiot_mvp`).

**Verification:** `pytest tests/unit/config/test_stages.py
tests/unit/app/cli/test_poison_cli.py` → 34 passed; `pyright` on both changed
source files → 0 errors; `ruff check` on all 4 changed files → clean.

**Evidence:** `_ai_tracking/diagnostics/CP2-T044_allseed_one_victim_stability.md`,
`_ai_tracking/run_logs/CP2-T044_mvp_run_plan.md`.

**What remains forbidden (unchanged):** fraction 0.05, B3, pairs/triples,
defenses, CICIoT2023, Edge-IIoTset, Phase F/G scaling, any cell outside the
exact 1620-cell matrix above, until CP2-T056/FB3/FB4.

**Next:** CP2-T045 (consolidate diagnostic glue into the single production
MVP run path) → execute the locked 1620-cell matrix → CP2-T046 (manifest/
result-sanity audit) → T047 (kill triggers) → T048 (drift check) → T049
(CONTINUE/STOP/PIVOT).

## 2026-06-16 | CP2-T045 | Bounded MVP run path consolidated; real 1620-cell manifest executed and written

CP2-T045 acceptance criteria met: single clean run path consolidated
(`mvp_matrix.py` → `mvp_manifest.py` → `mvp_run.py` → `cp2 run-mvp` CLI
command), no duplicated diagnostic glue, tests + pyright + ruff + Graphify
green. Then executed `datp cp2 run-mvp --base-dir outputs` against the real
FB1 N-BaIoT E=1 artifacts (5 training seeds, 9 clients each).

**Bug caught and fixed before execution:** `run_nbaiot_mvp` originally called
`enumerate_mvp_matrix` once per training seed with a singleton
`{training_seed: victims}` dict. `enumerate_mvp_matrix` always iterates the
full locked 5-seed pool internally (this is the contract the unit tests
lock — they call it once with all 5 seeds present), so every per-seed call
KeyError'd looking up the *next* seed's victim list. The unit tests didn't
catch this because they already passed a full 5-seed mapping; only the
integration test (which runs the real per-seed loop in `run_nbaiot_mvp`)
surfaced it. Fixed by loading all 5 seed collections first, then calling
`enumerate_mvp_matrix` exactly once with the complete mapping. Also found
the integration test fixture needed >=4 synthetic clients, since the locked
B4 `K=3` requires `eligible_count > k` — bumped from 3 to 4.

**Real execution result:** wall-clock ~70s, no GPU needed (calibration-
channel poisoning only operates on already-scored arrays). Manifest written
to `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`
(1.5 MB). Verified: `n_cells == len(results) == 1620` exactly; `training_seeds
== [0,1,2,3,4]`, `poisoning_seeds == [100..104]`; `mu_flag_threshold_by_training_seed
== {0: 0.005, 1: 0.0049, 2: 0.0056, 3: 0.0053, 4: 0.005}` (matches CP2-T044's
locked values exactly); `provenance.local_epochs == 1`; all 1620 rows have
`auroc_invariant == True`; all 405 `fraction == 0.0` rows have
`delta_tau == 0.0` exactly; exactly 9 distinct victim_ids (the 9 eligible
N-BaIoT clients).

**Files changed:** `src/datp/attacks/mvp_matrix.py`, `mvp_manifest.py`,
`mvp_run.py` (new); `source_strategies.py` (`objective_for_source`),
`app/cli/poison.py` (`run-mvp` command, registered under the `cp2` sub-app)
(edited); `tests/unit/attacks/test_mvp_matrix.py`, `test_mvp_manifest.py`,
`tests/integration/attacks/test_mvp_run.py` (new).

**Verification:** `pytest tests/unit/attacks` → 299 passed; `pytest
tests/integration/attacks/test_mvp_run.py -m integration` → 2 passed (115s,
real small-scale FL training + full sweep); `pyright` on all new/changed
files → 0 errors; `ruff check` → clean; `graphify update .` → 7650 nodes,
19194 edges, 437 communities.

**Evidence:** `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`,
`docs/tickets/phase_e_mvp/CP2-T045.md` (Audited line).

**What remains forbidden (unchanged):** fraction 0.05, B3, pairs/triples,
defenses, CICIoT2023, Edge-IIoTset, Phase F/G scaling, any cell outside the
exact 1620-cell matrix, until CP2-T056/FB3/FB4.

**Next:** CP2-T046 (manifest/result-sanity audit on the real 1620-cell
artifact) → T047 (kill triggers) → T048 (drift check) → T049
(CONTINUE/STOP/PIVOT).

## 2026-06-16 | CP2-T049 | Decision: CONTINUE (open Phase F) — evidence-grounded, one caveat carried forward

**Decision: CONTINUE.** Phase F (`phase_f_full_optional/`, CP2-T050–T055,
FB4) is now open for implementation work. This does **not** authorize any
new experiment run by itself — per CLAUDE.md §2.8/§9 and CP2-T056 §2/§12,
actual Phase F/G execution (fraction 0.05, multi-client pairs/triples,
defense, CICIoT2023 stretch) remains separately gated at **CP2-T056**, which
requires its own heavy-run authorization, mirroring the FB1 precedent. CONTINUE
only changes Phase F ticket statuses from "not started" to actionable.

**Evidence weighed (per roadmap §16 kill criteria + §12 primary-endpoint lock):**

1. **CP2-T046 (manifest audit): PASS.** Full 1620-cell artifact verified
   complete, provenance-correct, AUROC-invariant, cardinality-preserving;
   directional effects confirmed at full scale (HIGH/LOW 403–405 cells each
   sign-correct out of 405); 4 B4 sign-reversal cells flagged and explained
   (small-magnitude, cluster-boundary cases), not hidden.
2. **CP2-T047 (kill-trigger evaluation): NO KILL TRIGGER FIRES.** Kill
   criterion (1) [no material B2 shift] refuted strongly. Kill criterion (3)
   [B1/B2/B4 indistinguishable] refuted via a mechanistic identity
   (B1≈B2/9). Kill criteria (4)–(7) not fired / N/A.
3. **CP2-T048 (drift check): PASS.** No protocol-lock drift in the
   real-data execution path; `mu_flag_threshold` pre-poison lock confirmed
   architecturally; seed-scheme integrity confirmed at full scale (0/1620
   mismatches).
4. **New this ticket — closing the kill-trigger-(2) question precisely.**
   T047 had flagged kill criterion (2) ["threshold shifts do not translate
   into any interpretable downstream movement"] as an *open gap* because the
   manifest carries no literal victim ΔTPR. Re-reading roadmap §8/§12
   precisely: the primary endpoint assigns a **different** downstream metric
   per objective — victim ΔTPR for **raise**, `ΔCV(FPR)`/worst-client FPR
   for **lower**. The lower-narrative metric (`cv_fpr`) is *already* a
   manifest field, so it can be checked without any new code — pure
   read-only aggregation, same posture as T047's analysis. Computed
   `Δcv_fpr = cv_fpr(cell) − cv_fpr(f=0, same policy+training_seed)` for all
   405 `LOW_SCORE_BENIGN`/`threshold_lower` cells:

   | policy | fraction | mean Δcv_fpr (n=45) |
   |---|---|---|
   | b1_global | 0.10/0.20/0.40 | −0.0068 / −0.0127 / −0.0218 (homogenizing) |
   | b2_personalized | 0.10/0.20/0.40 | −0.0016 / +0.0046 / **+0.0692** (disparity-increasing) |
   | b4_cluster | 0.10/0.20/0.40 | −0.0105 / +0.0145 / **+0.0902** (disparity-increasing) |

   This is real, monotone-with-fraction, policy-differentiated downstream
   movement — **kill criterion (2) is refuted for the LOWER narrative**,
   confirmed by data, not just by the absence of a kill trigger. B1's
   opposite-sign (homogenizing) movement is itself an interpretable,
   policy-differentiated finding (global-mean dilution vs. per-client/cluster
   concentration), not a null result.

   **The RAISE narrative's downstream leg (victim ΔTPR) remains genuinely
   unmeasured** — no TPR/BA/F1 computation exists anywhere in
   `cell_runner.py`/`mvp_runner.py`/`metric_engine.py` (confirmed by grep,
   T047 §4). This is **not** a kill-trigger firing (Δτ for raise is strong,
   monotone, fully sign-consistent, materially significant per T046/T047)
   — it is an incomplete primary-endpoint leg for one of the two objectives.

**Why CONTINUE despite the open RAISE/ΔTPR leg:** no kill criterion fires;
this is the "mixed" scenario roadmap §15 explicitly anticipates and gives
safe wording for, not a kill/pivot scenario. The LOWER narrative's primary
endpoint is now fully evidenced (Δτ + ΔCV(FPR), both directionally
consistent and material). The RAISE narrative's Δτ leg is strong; only its
downstream-metric leg is outstanding, and it is closeable from
already-collected data (reuse `compute_b1_pair`/`compute_b2_pair`/
`compute_b4_pair`'s `tau_clean`/`tau_poisoned` against each victim's
already-loaded `test_attack` scores — no new poisoning, no new seeds, no
scope expansion). Per CP2-T049 §12's own blocking-conditions clause
("if evidence is insufficient to decide, gather more diagnostics rather
than guessing"), this is exactly the disposition for that one leg — except
the diagnostic-gathering for LOWER has *already* been done in this entry,
and RAISE's remaining piece is small, well-scoped, and does not block the
overall CONTINUE call.

**Binding condition carried forward (do not drop):** CP2-T057 (final
analysis & figures) must compute victim ΔTPR (and ΔBA where available) for
the RAISE cells before any RAISE-narrative primary claim is finalized in the
paper. Until that exists, RAISE claims must be worded as "Δτ raise effect
confirmed; downstream security-impact evidence pending" — not as a complete,
validated finding. This is recorded as a paper-notes do-not-claim and as an
explicit pre-start-audit item to carry into CP2-T057.

**What remains forbidden (unchanged):** fraction 0.05, B3, pairs/triples,
defenses, CICIoT2023, Edge-IIoTset, and any Phase F/G *execution*, until
CP2-T056 (or FB3/FB4) explicitly authorizes it. CONTINUE here opens ticket
*statuses* only.

**Evidence:** `_ai_tracking/audits/CP2-T046_mvp_manifest_result_sanity_audit.md`,
`_ai_tracking/audits/CP2-T047_kill_trigger_evaluation.md`,
`_ai_tracking/audits/CP2-T048_mvp_drift_check.md`,
`outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`,
the `Δcv_fpr` table above (ad hoc read-only aggregation, not committed,
same posture as T047's analysis script).

**Next:** Phase F tickets (CP2-T050–T055) open for implementation; CP2-T056
remains the actual execution gate. CP2-T057 inherits the binding condition
above.
