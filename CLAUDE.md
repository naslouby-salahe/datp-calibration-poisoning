# CLAUDE.md — Repository Instructions

This file is the root instruction document for all AI agents working in this repository.

---

## Active Project: CP2

**Title:** Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis

**CP2 is greenfield inside this repository.** Existing code is not automatically canonical. No backward compatibility is required unless a ticket explicitly says so.

**Do not import journal-extension scope into CP2.** The file `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md` is a contamination-boundary reference only.

---

## 1. Source-of-Truth Hierarchy

Use sources in this order:

1. Actual repository code, tests, configs, scripts, generated artifacts, and command output.
2. `docs/DATP_CP_Roadmap.md` — CP2 protocol of record.
3. `docs/tickets/README.md` — phase layout and scientific locks.
4. `docs/tickets/TICKET_INDEX.md` — authoritative CP2 ticket spec.
5. `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`
6. `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md`
7. `docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md`
8. `docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`
9. Individual ticket files: `docs/tickets/<phase>/CP2-T*.md`
10. `Blueprint.md`, `AGENTS.md`, `.claude/agents/*.md`, `.claude/skills/*.md`
11. `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md` — context only, never active plan.

Do not trust progress files alone. Inspect actual repository state. If a progress file contradicts repository reality, repository reality wins — record the contradiction.

---

## 2. Ticket Workflow

1. Read `docs/tickets/TICKET_INDEX.md` for the full ticket map.
2. Identify the active ticket from `CP2_PROGRESS.md`.
3. Read the active ticket file and all its listed dependencies.
4. Inspect actual code, configs, tests, manifests, outputs, `Additional_Docs/`, and prior audit evidence **before** writing any code.
5. Work the ticket scope only. Do not add features outside scope.
6. After completing work, update `CP2_PROGRESS.md` with evidence.
7. Do not skip dependencies.
8. Do not run final experiments before **CP2-T056**.
9. Do not run final analysis before **CP2-T057**.
10. Do not write the final paper package before **CP2-T058**.

---

## 3. CP2 Scientific Locks

### 3.1 Scope of attack

- CP2 is **calibration-channel poisoning only**.
- Training data is never poisoned.
- Model weights are never attacked.
- Aggregation is never attacked.
- Test data is never poisoned.
- No evasion, backdoor, or privacy claim.
- No deployment claim.
- No broad FL robustness claim.
- No generic poisoning claim.
- No journal-extension scope creep.

### 3.2 Dataset locks

- Primary: `REGIME_A_NBAIOT` — N-BaIoT physical-device clients.
- Optional stretch only, FB4-gated: CICIoT2023.
- **Forbidden for CP2:** Edge-IIoTset.

### 3.3 Policy locks

- Default policies: `B1_GLOBAL`, `B2_PERSONALIZED`, `B4_CLUSTER`.
- `B3` is **not** part of the CP2 default policy enum.

### 3.4 Attack mechanics locks

- Injection rule: `REPLACE_FIXED_BUDGET`.
  - `m_i = max(1, round(f · n_i))` positions replaced with values resampled **with replacement** from the victim-local reservoir.
  - Cardinality is preserved (`n_i` stays constant).
- Clean arrays must **never** be mutated in place. Always operate on a copy.
- Reservoirs are victim-local benign calibration scores.
- Test scores are **never** a reservoir.
- Training scores are **not** a reservoir.
- MVP objectives: `THRESHOLD_RAISE`, `THRESHOLD_LOWER`.
- MVP sources: `RANDOM_BENIGN`, `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`.
- MVP fractions: `{0, 0.10, 0.20, 0.40}`.
- Full-scope adds fraction `0.05` (conditional on CP2-T049 CONTINUE).

### 3.5 Seed locks

```
training_seed          = [0, 1, 2, 3, 4]
poisoning_seed         = [100, 101, 102, 103, 104]
analysis_seed          = [300, 301, 302, 303, 304]
compromise_pattern_seed = 400
```

Seed scheme: `numpy.random.SeedSequence([training_seed, poisoning_seed, client_id, scope_id])`.
**Do not use integer seed addition.**

### 3.6 B4 locks

- For N-BaIoT: K=3, k-means++, `n_init=10`, `max_iter=300`, `random_state=42`.
- Fingerprint: `[mean(E_i), std(E_i), skew(E_i), p95(E_i)]`.
- B4 deltas are **client-indexed effective-threshold deltas**.
- `Δτ_total = Δτ_agg + Δτ_churn`.
- **Do not compare raw k-means label IDs across runs.**

### 3.7 Metric and statistics locks

- `CV(FPR) = σ / µ` with **no epsilon** denominator.
- Always report coverage ratio alongside CV(FPR).
- AUROC must be invariant (test scores are unchanged by calibration-channel attack).
- **Do not treat 9 × 5 victim-seed deltas as 45 independent samples.**
- Use seed-level aggregates for policy-level inference.
- Bootstrap CI is on the **5 seed-level aggregates** (percentile default).
- Sign test is supporting evidence only (≥4/5 sign consistency).
- Holm-adjusted p-values are **descriptive only**.
- `mu_flag_threshold = round(M_clean / 8, 2 s.f.)` locked **before** any poisoned run.

### 3.8 Calibration-Pending clients

- Clients with fewer than `n_min=100` benign calibration samples are Calibration-Pending.
- They receive the global fallback threshold (`tau_global`).
- They are **excluded** from CV(FPR), eligible victim sets, and B4 clustering.
- Coverage ratio must be reported.

---

## 4. Coding Rules

- No backward compatibility by default.
- Prefer refactor over patching stale code.
- Use enums for scientific modes (objectives, sources, policies, scopes, defenses).
- Use typed dataclasses or typed Pydantic config models.
- Centralize constants and artifact paths.
- Do not hardcode scientific values in implementation modules.
- Do not use untyped dictionaries for core scientific config.
- Avoid `Any` unless unavoidable and justified.
- No AI comments. No TODO placeholders. No `type: ignore` unless justified and tracked.
- No duplicate implementations.
- Remove or quarantine stale journal logic.
- No in-place mutation of clean calibration arrays.

---

## 5. Test Taxonomy

```
tests/unit/        — smallest targeted tests; run first
tests/integration/ — impacted integration tests
tests/e2e/         — smoke or diagnostic runs
tests/fixtures/    — reusable builders (testsupport/)
```

### Escalation order (default per ticket)

1. Run the smallest relevant unit tests.
2. Run impacted integration tests.
3. Run the smallest relevant e2e or diagnostic command when required.
4. Run `pyright` / static checks if typed code or config changed.
5. Run `graphify update .` where applicable.

Do not run the full suite for every small ticket.

Run broader tests for:
- Refactor tickets
- Scientific drift tickets
- Milestone / phase-gate tickets
- Final experiment, analysis, and paper tickets (T056–T058)

---

## 6. Graphify

Graphify is **AVAILABLE** in this repository (graphifyy==0.8.39, installed 2026-06-15).

Status: `docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`

Canonical code-only update (no API key needed):

```bash
graphify update .
```

- Run after major refactors, package moves, or scope changes.
- Do not skip silently. If Graphify cannot run, document why in the status file.
- Save Graphify findings under `docs/tickets/_ai_tracking/graphify/`.

---

## 7. Paper Notes

If a ticket affects **claims, methods, metrics, artifacts, limitations, figures, tables, reviewer risks, or paper wording**, append notes to:

```
docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md
```

Each paper note must record:

- Claim enabled / claim blocked
- Limitation to disclose
- Figure or table affected
- Reviewer-risk relevance
- Do-not-claim reminder
- Evidence path

---

## 8. Progress and Decision Records

After every ticket:

- Update `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md` with evidence.
- If a decision was made (pivot, skip, hard-stop), record it in `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md`.

---

## 9. Hard Stop Rules

Stop and write a decision record if:

- Calibration-channel-only boundary would be violated.
- Training, model weights, aggregation, or test data would be poisoned.
- Edge-IIoTset would be used.
- CICIoT2023 stretch would run without the FB4 feasibility gate.
- A claim would be made without traceable evidence.
- An experiment would run before CP2-T056 authorization.
- A result would be fabricated or a `.tmp` placeholder treated as success.
- `mu_flag_threshold` would be set after, not before, poisoned runs.
- In-place mutation of clean arrays would occur.
- Integer seed addition would be used instead of `SeedSequence`.
- Journal-extension scope would be imported into CP2.

---

## 10. Tool Availability Check (run at session start)

```bash
graphify --version || true
python -m ruff --version
python -m pyright --version || pyright --version
python -m pytest --version
uv --version || true
```

Do not claim a tool passed unless it ran.

---

## 11. DATP Journal Work

When DATP journal work resumes (separate from CP2), use:

```
docs/journal/PRE_CODING_PLAN.md
docs/journal/CODING_PLAN.md
docs/journal/EXPERIMENT_PLAN.md
docs/journal/POST_EXPERIMENT_PLAN.md
docs/tickets/ticket_inventory.md
docs/tickets/ticket_progress.md
docs/tickets/human_interventions.md
```

These paths are stale for CP2 and must not be used for CP2 tickets.
