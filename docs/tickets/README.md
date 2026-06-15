# CP2 Implementation Tickets

Implementation ticket system for **CP2 — Calibration-Channel Poisoning of
Federated Threshold Personalization in IoT Anomaly Detection: A
Policy-Differentiated Vulnerability Analysis** (second conference paper extending
DATP).

**Protocol of record:** [`docs/DATP_CP_Roadmap.md`](../DATP_CP_Roadmap.md).
**Initial audit:** [`_ai_tracking/audits/CP2_INITIAL_REPO_AUDIT.md`](_ai_tracking/audits/CP2_INITIAL_REPO_AUDIT.md).
**Index:** [`TICKET_INDEX.md`](TICKET_INDEX.md).

> **Greenfield rule.** Existing code is not assumed correct. There is **no backward
> compatibility requirement** unless a ticket explicitly justifies one. Prefer
> audit → refactor → simplify → centralize → enforce with tests.

> **Evidence rule.** Do not trust progress files alone. Every ticket re-inspects the
> actual code, configs, tests, manifests, outputs, `Additional_Docs/`, and
> `docs/DATP_CP_Roadmap.md` before starting.

---

## 1. Phases and execution order

Execute phases in order. Within a phase, follow ticket-number order unless a
ticket's `Dependencies` say otherwise.

| Phase | Folder | Tickets |
|---|---|---|
| 00 — Setup & agent infrastructure | `phase_00_setup/` | CP2-T000 … CP2-T006 |
| A — Read-only scientific & code audit | `phase_a_audit/` | CP2-T007 … CP2-T015 (+ CP2-FB1, CP2-FB3) |
| B — Protocol lock & architecture | `phase_b_protocol_lock/` | CP2-T016 … CP2-T023 |
| C — Core implementation | `phase_c_core_implementation/` | CP2-T024 … CP2-T037 (+ CP2-FB2) |
| D — Smoke & diagnostics | `phase_d_smoke_validation/` | CP2-T038 … CP2-T041 |
| E — MVP preparation & audit | `phase_e_mvp/` | CP2-T042 … CP2-T049 |
| F — Optional full scope (conditional) | `phase_f_full_optional/` | CP2-T050 … CP2-T055 (+ CP2-FB4) |
| G — Experiment, analysis & paper | `phase_g_experiment_and_paper/` | CP2-T056 … CP2-T058 |

**The final three tickets are fixed:**
- **CP2-T056 — Run Final CP2 Experiments**
- **CP2-T057 — Build Final Analysis and Figures**
- **CP2-T058 — Write Paper Package and Claim Audit**

No earlier ticket may run the full final experiment; earlier tickets only run
smoke tests, diagnostics, dry-runs, and small MVP subsets.

### Periodic discipline tickets
Between every 5–10 normal tickets there is a **[REFACTOR]** checkpoint and a
**[DRIFT]** scientific-drift check. They are not optional. Refactor tickets
centralize enums/constants and run broader tests + Graphify; drift tickets compare
the implementation against `docs/DATP_CP_Roadmap.md` and `Additional_Docs/` and
block on contamination.

### Fallbacks (conditional)
`CP2-FB1..FB4` are **conditional**. Do not activate them unless their trigger fires.
Activation is an evidence-backed entry in
`_ai_tracking/decisions/CP2_DECISION_LOG.md`.

---

## 2. Dependency notes

- Phase A must not edit production code (read-only audit) except trivial doc notes.
- Phase B (protocol lock) gates Phase C: enums, config schema, constants, manifest,
  and seed scheme must exist before the injector/metrics are built.
- Phase D (smoke) must pass before Phase E (MVP). Phase E kill-trigger / pivot
  decision (CP2-T049) gates Phase F.
- Phase F is entirely conditional on MVP passing. Phase G is the final package.

---

## 3. How to update progress

After each ticket touch, append to
[`_ai_tracking/progress/CP2_PROGRESS.md`](_ai_tracking/progress/CP2_PROGRESS.md):
`date | ticket | status | commands | files | evidence path | next action`.
A ticket is `done` only with verified code + test + static-check evidence and a
re-audit; otherwise mark `needs reaudit`.

## 4. How to use Graphify

Graphify is **AVAILABLE** — graphifyy==0.8.39 installed 2026-06-15 (see
[`_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`](_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md)).
The default non-LLM invocation (no API key needed) is:

```bash
graphify update .
```

Every ticket carries a Graphify section: run it where applicable; otherwise
record the deferral with a reason in the status file. Never skip it silently.

## 5. How to write paper notes

When a ticket produces manuscript-relevant evidence, append a note to
[`_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md`](_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md)
(claim enabled / blocked / limitation / figure-table / reviewer-risk /
do-not-claim). The final paper ticket consolidates and audits them.

## 6. How to handle blockers

Stop and write a decision record in
[`_ai_tracking/decisions/CP2_DECISION_LOG.md`](_ai_tracking/decisions/CP2_DECISION_LOG.md)
with: exact blocker, command/action that failed, evidence, fallbacks attempted,
remaining safe work, next action. Then continue with any safe remaining work.

## 7. When is a ticket done

All of: scope implemented; smallest relevant tests pass (unit → integration →
e2e/diagnostic as applicable); pyright/ruff pass for changed typed code; relevant
scientific locks verified; Graphify run or deferred-with-reason; progress + paper
notes updated; acceptance criteria met; no wrappers/redirects/`shift_magnitude`-
style hardcoded science left behind.

---

## 8. Tracking folders

```
_ai_tracking/
  progress/     CP2_PROGRESS.md
  audits/       CP2_INITIAL_REPO_AUDIT.md, per-ticket audit notes
  diagnostics/  small dry-run / probe outputs
  decisions/    CP2_DECISION_LOG.md (blockers, fallbacks)
  manifests/    manifest schemas + instances
  run_logs/     curated run-log summaries
  paper_notes/  CP2_PAPER_NOTES_CONSOLIDATED.md
  graphify/     CP2_GRAPHIFY_STATUS.md
```

---

## 9. Non-negotiable CP2 scientific locks (summary)

Full text in `docs/DATP_CP_Roadmap.md`; each ticket repeats the relevant subset.

- **Scope:** calibration-channel poisoning **only**. Never poison training data,
  model weights, aggregation, or test data. No evasion/backdoor/privacy/deployment/
  broad-FL-robustness/generic-poisoning/journal claims.
- **Dataset:** primary `REGIME_A_NBAIOT` (physical-device clients). CICIoT2023 is
  optional stretch only (FB4-gated). **Edge-IIoTset forbidden.**
- **Policies:** default `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}`. **B3 must not
  be in the default enum.**
- **Attack:** objectives `{THRESHOLD_RAISE, THRESHOLD_LOWER}`; sources
  `{RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}`; fractions
  `{0, 0.10, 0.20, 0.40}`; `REPLACE_FIXED_BUDGET`; `SINGLE_CLIENT` for MVP.
  Victim-local reservoirs; test scores never a reservoir; training scores not a
  reservoir; fixed-size **with-replacement** replacement; **no in-place mutation**
  of clean arrays.
- **Seeds:** `training=[0..4]`, `poisoning=[100..104]`, `analysis=[300..304]`,
  `split=[200..204]` (only if new splits), `compromise_pattern_seed=400`. Use
  `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` — **never
  integer addition**.
- **Artifacts:** clean = conference-faithful DATP, **E=1** (reject E=5, reject
  journal-only). Clean and poisoned share training_seed, AE, split, test scores,
  victim plan; poisoning is the only stochastic difference.
- **B4:** N-BaIoT `K=3`, k-means++, `n_init=10`, `max_iter=300`, `random_state=42`,
  fingerprint `[mean,std,skew,p95]`. Deltas client-indexed (effective thresholds,
  never raw cluster labels). Decompose `Δτ_total = Δτ_agg + Δτ_churn`.
- **Metrics:** `Δτ = τ_pois − τ_clean`; `Δτ_rel = Δτ/max(|τ_clean|, ε)`;
  materiality `δ_τ,i = 0.1·IQR(clean cal scores_i)`; `CV(FPR)=σ/µ` (no ε); guard
  with IQR(FPR), max−min FPR, WorstClientFPR. Lock
  `mu_flag_threshold = round(M_clean/8, 2 s.f.)` before any poisoned run. AUROC
  invariant (test scores unchanged).
- **Statistics:** two-layer unit (never 9×5 = 45 independent); per-victim paired
  seed deltas; seed-level aggregates for policy inference; ≥4/5 sign consistency;
  strict-majority of eligible feasible victims; bootstrap CI on 5 seed-level
  aggregates (DATP variant if found, else percentile); exact paired sign test
  supporting only; Holm descriptive only.
