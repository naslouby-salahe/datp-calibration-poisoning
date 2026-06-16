# CP2-T047 — Kill-Trigger Evaluation

**Date:** 2026-06-16
**Ticket:** CP2-T047 (results-audit / decision-input)
**Auditor:** automated session

**Verdict: NO KILL TRIGGER FIRES. The CP2 hypothesis is viable on the bounded
MVP evidence.** Six of the seven pre-registered kill triggers (roadmap §16)
are clearly refuted by the audited 1620-cell manifest (CP2-T046) plus the
two-layer statistical inference run for this ticket. The seventh (trigger 2,
downstream-metric movement) is **not fully closeable** with the artifacts
the bounded MVP currently produces — the manifest carries the Δτ-materiality
(ASR) proxy but not literal victim ΔTPR/ΔBA — and is flagged as a residual
evidentiary gap for CP2-T049 to weigh explicitly, not silently resolved
either way. One narrow confound is flagged under trigger 3's evidence
(B4_CLUSTER / RANDOM_BENIGN / f=0.40 shows a small but bootstrap-CI-significant
non-null mean, mechanistically attributable to cluster-churn variance, not a
directional bias) — does not change the trigger-3 verdict.

This evaluation is evidence-based per CP2-T046's audited manifest
(`outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`) plus a
fresh two-layer statistical pass (bootstrap CI on 5 seed-level aggregates,
sign test, per-victim ≥4/5 sign consistency, strict-majority-of-victims rule)
computed read-only from that manifest using the already-tested
`datp.attacks.inference` module (CP2-T035). No new production code was
added (T047's coding lock is read-only); the analysis script is a one-off,
not committed to the repository.

---

## 0. Method

For each of the 27 non-zero-fraction `(policy, source, fraction)` cells
(`B1_GLOBAL/B2_PERSONALIZED/B4_CLUSTER` × `HIGH_SCORE_BENIGN/LOW_SCORE_BENIGN/
RANDOM_BENIGN` × `{0.10, 0.20, 0.40}`):

- **Layer 1 (per-victim):** for each of the 9 eligible victims, count how many
  of its 5 paired `(training_seed, poisoning_seed)` deltas have the
  source-implied sign (HIGH→`Δτ>0`, LOW→`Δτ<0`); a victim is "sign-consistent"
  at `≥4/5`. RANDOM_BENIGN has no directional expectation (`objective=None`,
  per `objective_for_source`) and is excluded from this directional count.
- **Strict-majority rule (roadmap §9):** `≥ floor(9/2)+1 = 5` of the 9
  eligible-and-feasible victims must be sign-consistent. All 9 victims were
  feasible in every cell (CP2-T046: `n_eligible==9`, `coverage_ratio==1.0`
  on all 1620 rows — FB2 does not bind on N-BaIoT, confirmed).
- **Layer 2 (seed-level aggregate):** `δ_s = mean(Δτ_{v,s})` over the 9
  feasible victims, for each of the 5 poisoning seeds; percentile bootstrap
  CI (10,000 resamples, `analysis_seed=300`) and a supporting sign test on
  the 5 aggregates, via `compute_seed_aggregates` / `bootstrap_seed_aggregates`
  / `sign_test` (unchanged from CP2-T035/T044).
- **Materiality rate (ASR proxy):** fraction of the 45 `(victim, seed)` pairs
  in the cell with `is_victim_significant == True`, i.e.
  `|Δτ| ≥ 0.1·IQR(clean cal)` (the roadmap §8 materiality scale `δ_{τ,i}`,
  already computed per-row in the manifest by `metric_engine.py`).

## 1. Full results table (27 cells, non-zero fraction)

| Policy | Source | f | Direction | Victims sign-cons. (of 9) | Strict majority | Seed-agg mean Δτ | Bootstrap CI | Sign test (5/5) | Materiality rate |
|---|---|---|---|---|---|---|---|---|---|
| B1 | HIGH | 0.10 | raise | 9 | YES | +0.0315 | [0.0286, 0.0353] | 5-0 | 0.778 |
| B1 | HIGH | 0.20 | raise | 9 | YES | +0.0612 | [0.0556, 0.0667] | 5-0 | 0.956 |
| B1 | HIGH | 0.40 | raise | 9 | YES | +0.1015 | [0.0954, 0.1077] | 5-0 | 1.000 |
| B1 | LOW | 0.10 | lower | 9 | YES | −0.0052 | [−0.0058, −0.0048] | 0-5 | 0.467 |
| B1 | LOW | 0.20 | lower | 9 | YES | −0.0102 | [−0.0107, −0.0097] | 0-5 | 0.600 |
| B1 | LOW | 0.40 | lower | 9 | YES | −0.0185 | [−0.0192, −0.0178] | 0-5 | 0.778 |
| B1 | RANDOM | 0.10 | n/a | n/a | n/a | +0.0003 | [−0.0002, 0.0006] (incl. 0) | n/a | 0.067 |
| B1 | RANDOM | 0.20 | n/a | n/a | n/a | +0.0003 | [−0.0009, 0.0016] (incl. 0) | n/a | 0.111 |
| B1 | RANDOM | 0.40 | n/a | n/a | n/a | −0.0003 | [−0.0010, 0.0004] (incl. 0) | n/a | 0.156 |
| B2 | HIGH | 0.10 | raise | 9 | YES | +0.2839 | [0.2578, 0.3177] | 5-0 | 1.000 |
| B2 | HIGH | 0.20 | raise | 9 | YES | +0.5504 | [0.5003, 0.6005] | 5-0 | 1.000 |
| B2 | HIGH | 0.40 | raise | 9 | YES | +0.9139 | [0.8588, 0.9690] | 5-0 | 1.000 |
| B2 | LOW | 0.10 | lower | 9 | YES | −0.0469 | [−0.0518, −0.0436] | 0-5 | 0.889 |
| B2 | LOW | 0.20 | lower | 9 | YES | −0.0914 | [−0.0962, −0.0871] | 0-5 | 0.978 |
| B2 | LOW | 0.40 | lower | 9 | YES | −0.1668 | [−0.1732, −0.1599] | 0-5 | 1.000 |
| B2 | RANDOM | 0.10 | n/a | n/a | n/a | +0.0029 | [−0.0014, 0.0057] (incl. 0) | n/a | 0.467 |
| B2 | RANDOM | 0.20 | n/a | n/a | n/a | +0.0030 | [−0.0078, 0.0143] (incl. 0) | n/a | 0.511 |
| B2 | RANDOM | 0.40 | n/a | n/a | n/a | −0.0024 | [−0.0090, 0.0033] (incl. 0) | n/a | 0.556 |
| B4 | HIGH | 0.10 | raise | 9 | YES | +0.2260 | [0.1848, 0.2626] | 5-0 | 0.978 |
| B4 | HIGH | 0.20 | raise | 9 | YES | +0.4758 | [0.4241, 0.5275] | 5-0 | 1.000 |
| B4 | HIGH | 0.40 | raise | 9 | YES | +0.8817 | [0.7915, 0.9711] | 5-0 | 1.000 |
| B4 | LOW | 0.10 | lower | 9 | YES | −0.0374 | [−0.0630, −0.0166] | 0-5 | 0.644 |
| B4 | LOW | 0.20 | lower | 9 | YES | −0.0774 | [−0.0965, −0.0584] | 0-5 | 0.756 |
| B4 | LOW | 0.40 | lower | **8** | YES | −0.1419 | [−0.1550, −0.1288] | 0-5 | 0.978 |
| B4 | RANDOM | 0.10 | n/a | n/a | n/a | +0.0074 | [−0.0001, 0.0203] (incl. 0) | n/a | 0.267 |
| B4 | RANDOM | 0.20 | n/a | n/a | n/a | +0.0020 | [−0.0038, 0.0097] (incl. 0) | n/a | 0.311 |
| B4 | RANDOM | 0.40 | n/a | n/a | n/a | **−0.0159** | **[−0.0233, −0.0065] (excl. 0)** | n/a | 0.622 |

The single bold row (`B4_CLUSTER`/`RANDOM_BENIGN`/`f=0.40`) is the one cell
in the entire 27-cell grid where the bootstrap CI excludes zero for a
non-directional source — flagged and discussed in §3.

## 2. Kill-trigger (1) — "no material threshold shift for B2 under HIGH/LOW even at f=0.40"

**Does not fire — strongly refuted.** `B2_PERSONALIZED` at every fraction,
both directions, shows large, materially significant, fully sign-consistent
effects:

- `B2/HIGH/f=0.40`: seed-aggregate mean `+0.914`, CI `[0.859, 0.969]`
  (excludes zero by a wide margin), 9/9 victims sign-consistent, 5/5 seed
  sign test, materiality rate `1.000` (all 45 victim×seed pairs cross the
  ASR bar).
- `B2/LOW/f=0.40`: seed-aggregate mean `−0.167`, CI `[−0.173, −0.160]`, 9/9
  victims, 5/5 seeds, materiality rate `1.000`.
- The effect is monotone in fraction for both directions
  (`B2/HIGH`: `0.10→0.284, 0.20→0.550, 0.40→0.914`;
  `B2/LOW`: `0.10→−0.047, 0.20→−0.091, 0.40→−0.167`), matching the roadmap's
  smoke invariant 4/5 and the CP2-T043/T044 diagnostics.

## 3. Kill-trigger (3) — "B1/B2/B4 remain indistinguishable even after blast radius and spillover"

**Does not fire — clearly distinguishable, and the separation is
mechanistically explainable, not noise.**

- Per-victim magnitude ordering at `f=0.40`/HIGH: `B2 (0.914) ≈ B4 (0.882) >
  B1 (0.102)`. This matches the underlying mechanism exactly: B1's
  `tau_global` is the mean of 9 per-client thresholds, so a single victim's
  shift of `~0.914` (B2's value, since B2's victim threshold shift is
  un-diluted) divided by 9 clients is `0.914/9 = 0.1016` — within rounding of
  the observed B1 value `0.1015`. This is a clean, falsifiable mechanistic
  cross-check, not a coincidence.
- B4 sits close to B2 in raw victim-shift magnitude (cluster-mean dilution
  is partial, not full division-by-9 like B1) but with materially higher
  cross-cell variance (CP2-T044 already found B4's across-seed Δτ CV is
  ~2× B1/B2's) — consistent with K=3 cluster-membership sensitivity.
- This reconciles with CP2-T046's `blast_fraction` finding (`B1=0.559 >
  B4=0.447 > B2=0.091`, a *different* axis — breadth of clients affected,
  not the victim's own Δτ magnitude): B1 spreads a small shift to all 9
  clients via the shared global mean (high blast, low per-victim magnitude);
  B2 concentrates a large shift on exactly 1 client (low blast, high
  magnitude); B4 is intermediate on both axes. The two metrics are
  consistent, not contradictory, once the mechanism is made explicit.
- **Confound flagged, not trigger-altering:** `B4_CLUSTER`/`RANDOM_BENIGN`/
  `f=0.40` is the only one of 9 RANDOM_BENIGN cells where the seed-level
  bootstrap CI excludes zero (`[−0.0233, −0.0065]`), and its materiality rate
  (`0.622`) is markedly higher than B4's other RANDOM cells (`0.267`,
  `0.311`). Mechanistically attributable to the locked B4 decomposition
  `Δτ_total = Δτ_agg + Δτ_churn` (CP2-T031): at the largest fraction, even
  *unbiased* random resampling perturbs a victim's fingerprint
  (`[mean, std, skew, p95]`) enough to occasionally trigger cluster
  reassignment, and churn is not symmetric around zero by construction. The
  magnitude (`|mean| = 0.016`) is roughly 6–13× smaller than the directional
  B4 effects at the same fraction (`0.882`, `0.142`), so RANDOM_BENIGN
  remains a usable near-null control in relative terms — but this specific
  cell should not be cited as "exactly null" without this caveat, and is a
  candidate footnote for the B4 decomposition appendix (roadmap §11).

## 4. Kill-trigger (2) — "threshold shifts do not translate into any interpretable downstream movement"

**Not fully closeable with current artifacts — flagged as a residual
evidentiary gap, not resolved either way.**

The roadmap (§8 secondary metrics; §9, §12 primary-endpoint rule: "material
`Δτ` with correct sign linked to **≥1 downstream metric**") requires victim
`ΔTPR` (raise) or `ΔCV(FPR)`/worst-client FPR (lower) movement, not just `Δτ`
itself, to close a primary claim. The bounded-MVP manifest schema
(`Cp2MvpResultRow`, CP2-T045) carries `delta_tau`, `delta_tau_rel`,
`is_victim_significant` (the ASR/materiality proxy on `Δτ` itself),
`cv_fpr`/`mean_fpr`/`coverage_ratio` (fleet-level, not victim-`ΔTPR`),
`blast_fraction`/`n_spillover` — but **no literal per-victim `ΔTPR`, `ΔBA`,
`ΔMacroF1`, or `ΔP10-ClientF1`** field. This is a real, not cosmetic, gap
against the roadmap's own metric list (§8) — `metric_engine.py`/T033 and
`diagnostics.py`/T034 built `Δτ`, CV(FPR), AUROC, ASR, blast radius, and
spillover, but not the victim-level downstream detection-rate metrics.

This ticket's own coding lock is **read-only** ("Read-only; typed;
evidence-backed; no overclaim" — §6 of the ticket), so computing the missing
metric is explicitly out of scope for T047 itself; doing so would require
either extending `Cp2MvpResultRow` or a separate derived-artifact pass
re-applying `tau_clean`/`tau_poisoned` (recoverable from `cell_runner.py`'s
`recompute_pair` primitives) against each victim's already-loaded
`test_attack` scores. That is a bounded, low-risk follow-on (no new
scientific values, reuses already-tested production primitives) but is new
production work, not an audit, and is therefore deferred rather than done
inside this read-only ticket.

**Best available proxy, for the record:** the ASR/materiality indicator
(`is_victim_significant`, `Δτ`-based) is strongly and consistently positive
across all 6 directional `(policy, source)` combinations at `f≥0.20`
(materiality rate `≥0.60` everywhere except `B1/LOW/f=0.10` at `0.467`), and
the bootstrap CIs for the directional cells never include zero. This is
adjacent to, but not the same evidentiary claim as, "the victim's detection
rate measurably changed." **Recommendation for CP2-T049:** treat trigger (2)
as "not observed to fire on the closest available proxy, but not literally
verified" — a residual risk to disclose in any paper claim (do-not-claim:
"primary endpoint fully closed per roadmap §12") until a dedicated
downstream-metric diagnostic is run, which can reuse existing
`cell_runner.py` + `Cp2ScoreCollection.test_attack` primitives without any
new scientific design.

## 5. Kill-trigger (4) — "the effect appears only under the diagnostic upper bound, not the gray-box model"

**Does not fire — not applicable; no diagnostic-upper-bound run exists to
compare against.** CP2's `select_reservoir`/`source_strategies.py` explicitly
guards `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` and
`WHITE_BOX_DIAGNOSTIC_ONLY` out of the MVP/full matrix
(`DiagnosticSourceError`, CP2-T029) — confirmed never invoked in the bounded
MVP (`source` field in all 1620 manifest rows is one of the three MVP-locked
enum values only). The entire MVP was run under the gray-box model by
construction, so this trigger cannot fire one way or the other from MVP
evidence; it remains relevant only if a future diagnostic-upper-bound
comparison is run (out of CP2-T047 scope).

## 6. Kill-triggers (5)/(6)/(7) — repo cleanliness / journal separation / "generic poisoning" framing

**Do not fire — already evidenced by prior audits, re-confirmed here by
citation, no new evidence needed:**

- (5) repo cleanliness: CP2-T028 (quarantined-module removal), CP2-T036
  (duplication audit), the Phase A/B/C/D audit-reconcile pass — no
  timeline-breaking refactor outstanding.
- (6) journal separation: CP2-T002, CP2-T023, CP2-T032, CP2-T037, CP2-T040 —
  repeated `rg` contamination scans, all clean (prohibition-context only).
- (7) "generic poisoning" framing: the calibration-channel-only boundary
  (training/model/aggregation/test never touched) has been verified at
  every audit gate (T009, T023, T032, T037, T041, T043, T046) including the
  AUROC-invariance check on the real 1620-cell manifest (1620/1620 True) —
  the reviewer-risk framing in roadmap §14 row 1 stands on real-data
  evidence now, not just a design intention.

## 7. Acceptance criteria check (ticket §11)

- Every kill-trigger evaluated with evidence: **YES** (§2–§6).
- Viability verdict recorded: **YES** — no kill trigger fires; trigger (2)
  flagged as an open evidentiary gap rather than a false "pass."
- `pyright`: 0 errors (no new production code; ad hoc analysis script not
  committed to the repository).

**Next:** CP2-T048 (MVP drift check), then CP2-T049 (continue/stop/pivot
decision) — CP2-T049 should explicitly weigh the trigger-(2) gap and the
B4/RANDOM/f=0.40 confound noted in §3 when forming its decision rationale.
