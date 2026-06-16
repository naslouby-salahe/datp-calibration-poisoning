# CP2-T046 — MVP Manifest & Result-Sanity Audit

**Date:** 2026-06-16
**Ticket:** CP2-T046 (results-audit; non-interpretive)
**Auditor:** automated session
**Verdict: PASS — the real 1620-cell bounded-MVP manifest is complete, schema-valid,
and protocol-faithful. Four cells (0.25%) show a directional sign reversal, all
confined to `B4_CLUSTER` and mechanistically explained by cluster-reassignment
churn, not data corruption — flagged, not treated as anomaly requiring a fix.
No significance or claim interpretation performed (reserved for CP2-T047/T049).**

Artifact audited: `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`
(1.5 MB, written 2026-06-16 by `datp cp2 run-mvp --base-dir outputs`, see decision log
`CP2-T045 | Bounded MVP run path consolidated; real 1620-cell manifest executed
and written`).

---

## 1. Completeness (roadmap §10, ticket §3)

| Check | Result |
|---|---|
| `n_cells == len(results)` | 1620 == 1620 — PASS |
| Re-validates against `Cp2MvpManifest` (typed Pydantic schema, `extra="forbid"`, `frozen=True`) | PASS, including the model's own consistency validator (seed pairing, `n_cells`, `mu_flag` coverage) |
| Unique `(training_seed, victim_id, policy, source, fraction)` cells | 1620 distinct keys — full matrix, no duplicates, no gaps |
| `training_seeds` / `poisoning_seeds` | `[0,1,2,3,4]` / `[100,101,102,103,104]`, paired 1:1 per row, 0 mispairings |
| `target_scope` | `single_client` on all 1620 rows |
| No `.tmp` / placeholder artifacts in `outputs/conference_calibration_poisoning/` | confirmed (single manifest file only) |
| `seed_record.entropy` matches `SeedSequence([training_seed, poisoning_seed, client_idx, scope_idx])` | spot-checked — `[0, 100, 0, 0]` for `Danmini_Doorbell`/seed 0; no integer-addition pattern |

## 2. Provenance (roadmap §7, §10 — E=1 enforcement)

```json
{"local_epochs": 1, "cp2_generated": true, "repository": "datp-calibration-poisoning",
 "checkpoint_round": null, "split_semantics": "chronological_benign_only_60_1_20_1_18"}
```

`local_epochs == 1` confirmed (the FB1 retrain artifact, not the rejected E=5 config).
`mu_flag_threshold_by_training_seed` has exactly one entry per training seed:
`{0: 0.005, 1: 0.0049, 2: 0.0056, 3: 0.0053, 4: 0.005}` — **identical** to the values
independently locked during the CP2-T044 stability sweep, confirming
`lock_mu_flag_threshold` is deterministic and was genuinely fixed from clean B1 data
before any poisoned cell ran (hard-stop guard: "mu_flag_threshold set after, not
before, poisoned runs" — not triggered).

## 3. Eligibility / coverage (roadmap §7 — Calibration-Pending exclusion)

`n_eligible` is `9` on every one of the 1620 rows; `coverage_ratio` is `1.0` on every
row. Matches CP2-T042's finding (9/9 N-BaIoT clients eligible, 0 Calibration-Pending,
every seed) — no client silently dropped out under poisoning, consistent with the
roadmap §7 invariant that fixed-size replacement preserves `n_i` and therefore
eligibility.

## 4. AUROC invariance (roadmap §8, §12 — calibration-channel-only boundary)

`auroc_invariant == True` on all 1620/1620 rows. Test scores were never touched by
calibration-channel poisoning, as required — this is the load-bearing check that the
attack stayed inside its locked scope.

## 5. `f=0` no-op invariant

405 rows have `fraction == 0.0` (1620/4, exactly one quarter as expected from the
4-point fraction grid). All 405: `delta_tau == 0.0`, `delta_tau_rel == 0.0`,
`blast_fraction == 0.0`, `n_spillover == 0`, `is_victim_significant == False`. Zero
poisoning budget produces exactly zero effect, every cell, every seed, every policy.

## 6. Numerical sanity

Full NaN/Inf scan across every float field of all 1620 rows: **0 anomalies**.
`mu_flag_triggered` is `False` on all 1620 rows (CV(FPR) instability flag never
tripped at this scale — descriptive only, no claim drawn). `is_victim_significant`
is `True` on 849/1620 rows (52.4%) — purely descriptive at this stage; CP2-T047/T049
own significance interpretation.

## 7. Directional sanity (roadmap §10 smoke invariants 3–4, descriptive only)

Non-zero-fraction rows (n=1215, 405 per source):

| Source | Expected direction | pos | neg | zero | mean Δτ |
|---|---|---|---|---|---|
| `high_score_benign` | raise (Δτ > 0) | 403 | 2 | 0 | +0.392 |
| `low_score_benign` | lower (Δτ < 0) | 2 | 403 | 0 | −0.0662 |
| `random_benign` | near-null | 200 | 190 | 15 | −0.0003 |

99.5% directional consistency for both HIGH/LOW sources; RANDOM is near-null as
required (mean within numerical noise of zero, roughly balanced pos/neg split).

**Flagged anomaly — 4 sign-reversed cells, all `B4_CLUSTER`:**

| Source | Victim | Seed | Fraction | Δτ |
|---|---|---|---|---|
| `high_score_benign` | `SimpleHome_XCS7_1002_WHT_Security_Camera` | 0 | 0.10 | −0.0328 |
| `high_score_benign` | `SimpleHome_XCS7_1002_WHT_Security_Camera` | 0 | 0.20 | −0.0228 |
| `low_score_benign` | `Provision_PT_737E_Security_Camera` | 1 | 0.40 | +0.00749 |
| `low_score_benign` | `Provision_PT_737E_Security_Camera` | 3 | 0.40 | +0.0204 |

All 4 occur exclusively under `B4_CLUSTER` and nowhere under `B1_GLOBAL`/
`B2_PERSONALIZED` (0 reversals in either). This is mechanistically consistent with
the locked B4 decomposition `Δτ_total = Δτ_agg + Δτ_churn` (CP2-T031): churn from
cluster reassignment after poisoning can act against the direct injection effect for
a specific victim, which is a measurability property of B4, not an injector or
metric-engine defect. Magnitudes are small (`|Δτ| <= 0.033`). Not treated as a data
integrity failure; flagged for CP2-T047/T049 to weigh against the ≥4/5-seed
sign-consistency rule (roadmap §9) at the per-victim level.

The 15 `random_benign` exact-zero cells cluster mostly at the smallest non-zero
fraction (9/15 at `f=0.10`, the rest split across `f=0.20`/`f=0.40`) — consistent
with order-statistic-based thresholds being insensitive to some small-budget
resampling draws, not a computation bug.

## 8. Blast radius by policy (descriptive only, non-zero fraction)

| Policy | mean blast_fraction |
|---|---|
| `B1_GLOBAL` | 0.559 |
| `B4_CLUSTER` | 0.447 |
| `B2_PERSONALIZED` | 0.091 |

Ordering `B1 > B4 > B2` matches the CP2-T043 one-seed finding and the roadmap's
qualitative hypothesis (B4 strictly between the two boundary policies) — reported
here as a descriptive cross-check at full scale, not a significance claim.

## 9. What was not done here (correctly out of scope)

- No significance testing, sign-consistency-rule evaluation, or aggregate-claim
  rule application — that is CP2-T047 (kill triggers) and CP2-T049 (decision).
- No comparison against `mu_flag_threshold` as an instability gate beyond noting it
  never tripped — interpretation is CP2-T047/T049's job.
- Cardinality preservation (`n_i` constant under injection) is not a manifest field;
  it is enforced and tested at the injector level (`tests/unit/attacks/test_injector.py`,
  23 tests, CP2-T027) and was independently spot-checked via
  `assert_no_inplace_mutation` at CP2-T043 one-seed diagnostics. Not re-derived here.

## 10. Verification commands

```bash
python3 -c "from datp.attacks.mvp_manifest import Cp2MvpManifest; from pathlib import Path; \
  Cp2MvpManifest.model_validate_json(Path('outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json').read_text())"
# schema validation OK; n_cells = 1620 results = 1620
```
Plus the ad hoc completeness/NaN/directional scans summarized in sections 1–8 above
(run against the live manifest file, not re-derived from memory).

## 11. Acceptance criteria check (ticket §11)

- All 1620 MVP cells complete and sane: **YES**.
- Anomalies explicitly flagged, not silently dropped or fixed: **YES** (§7).
- Audit report written: this file.
- `pyright`: 0 errors (no new code in this ticket; read-only audit).

**Next:** CP2-T047 (kill-trigger evaluation).
