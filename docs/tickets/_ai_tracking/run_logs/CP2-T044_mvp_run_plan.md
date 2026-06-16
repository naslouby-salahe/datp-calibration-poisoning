# CP2-T044 — Bounded MVP Run Plan

**Date:** 2026-06-16
**Ticket:** CP2-T044 (authorizes the bounded MVP execution itself, per the
governance fix recorded in the decision log — CP2-T056 gates only the later
final/full CP2 experiments, not this run)
**Status:** LOCKED — this is the exact, bounded matrix authorized to run.
Anything outside this matrix requires CP2-T056 (or FB3/FB4 for stretch scope).

---

## 1. Matrix definition

| Axis | Locked values | Count |
|---|---|---|
| Dataset | `REGIME_A_NBAIOT` only | 1 |
| Scale | `ExperimentScale.MVP` | 1 |
| Target scope | `PoisoningTargetScope.SINGLE_CLIENT` only | 1 |
| Policy | `B1_GLOBAL`, `B2_PERSONALIZED`, `B4_CLUSTER` | 3 |
| Source | `RANDOM_BENIGN`, `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN` | 3 |
| Fraction | `0.0, 0.10, 0.20, 0.40` (`CP2_MVP_FRACTIONS`) | 4 |
| Victim | all 9 eligible N-BaIoT clients (identical set across all 5 seeds, confirmed CP2-T043/T044 diagnostics) | 9 |
| (training_seed, poisoning_seed) | paired 1:1: `(0,100), (1,101), (2,102), (3,103), (4,104)` — **not** a 5×5 cross product | 5 |

**Total cells: 3 × 3 × 4 × 9 × 5 = 1620.**

Each cell = one `run_mvp_cell(...)` call, producing a clean-vs-poisoned
`MvpCellResult` (per-eligible-client Δτ, fleet FPR/CV, AUROC records for both
the clean and poisoned condition).

`objective` (`THRESHOLD_RAISE` / `THRESHOLD_LOWER`) is recorded as metadata
derived from source direction (HIGH→RAISE, LOW→LOWER) for ASR computation
in CP2-T046/T047; it is not an independent sweep axis — crossing it with
source would double-count (HIGH source has no meaningful THRESHOLD_LOWER
interpretation, and vice versa). RANDOM_BENIGN is the non-directional
control and is not paired with an ASR objective.

### Explicitly excluded from this run (forbidden until CP2-T056 / FB3 / FB4)

- `B3` (not in the CP2 default policy enum at all).
- Fraction `0.05` (Full-scope only, FB4-gated).
- `PoisoningTargetScope.MULTI_CLIENT` (pairs/triples) and
  `ALL_CLIENTS_DIAGNOSTIC_ONLY` as an actual joint-poisoning scope (the
  per-victim *loop* used in CP2-T043's "all-victims" diagnostic and in this
  run is 9 independent `SINGLE_CLIENT` cells, not a joint multi-client
  poisoning pass).
- `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` source (diagnostic-only, gated
  behind `allow_diagnostic=True`, never enters the MVP/full matrix per
  `source_strategies.py`).
- Any defense (`PoisoningDefense`), CICIoT2023, Edge-IIoTset.
- Phase F/G scaling, expanded seed lists, venue strategy.

## 2. mu_flag_threshold locking

Locked once per training seed from that seed's own clean B1 eligible-client
mean FPR, **before** any poisoned cell for that seed runs (CLAUDE.md §3.7,
§9). Verified per-seed values (CP2-T044 stability diagnostic):

```
training_seed=0 → mu_flag_threshold=0.0050
training_seed=1 → mu_flag_threshold=0.0049
training_seed=2 → mu_flag_threshold=0.0056
training_seed=3 → mu_flag_threshold=0.0053
training_seed=4 → mu_flag_threshold=0.0050
```

The MVP run re-locks these identically (same deterministic computation from
the same clean artifacts) and records each in the run-level manifest before
sweeping that seed's 324 cells (3×3×4×9).

## 3. Artifact strategy (resolves the Cp2CellId/victim-granularity question)

`datp.artifacts.poison_layout.Cp2Layout` / `Cp2CellId` define the **full-scope
(Phase G, CP2-T056-gated)** per-cell directory tree
(`.../poison_<seed>/{poisoned_scores,threshold_deltas,cell_metrics,...}`).
`Cp2CellId` does not carry a victim dimension because full-scope cells are
not assumed to be `SINGLE_CLIENT`-only.

The bounded MVP does **not** use that per-cell tree. `CP2-T018` locks a
dedicated, single manifest filename for exactly this purpose:
`Cp2Layout.nbaiot_mvp_manifest()` → `nbaiot_mvp_manifest.json`. The MVP run
writes **one file** at that path, with two sections:

1. **Run-level provenance** (matrix definition per this document's §1, the 5
   per-seed `mu_flag_threshold` values, dataset provenance — E=1, repository,
   split semantics, reusing `Cp2ProvenanceRecord` — and a generation
   timestamp).
2. **Results array**: 1620 entries, one per
   `(policy, source, fraction, victim, training_seed, poisoning_seed)` cell,
   recording Δτ, fleet FPR/CV(FPR)/coverage, AUROC-invariance check, blast
   radius, and spillover — the same fields already produced by
   `run_mvp_cell` + `datp.attacks.diagnostics.compute_blast_radius` /
   `compute_spillover`, the same primitives exercised in CP2-T043/T044.

This keeps the bounded MVP's footprint to exactly the one manifest filename
CP2-T018 already locked for this purpose (no new artifact-name constant
invented), avoids 1620 per-cell directories, and does not require any change
to the full-scope `Cp2CellId`/`Cp2Layout` schema (no scope creep into Phase
G's layout).

## 4. Resource estimate

Directly benchmarked on this machine (in-process, no GPU — this is pure
recompute over already-scored, already-loaded calibration/test arrays; no
federated training occurs in the MVP):

```
load_real_score_collection (1 seed):  0.24s
lock_mu_flag_threshold + AUROC cache:  2.90s
324 cells (1 seed, all policy/source/fraction/victim combos): 8.54s (26.4ms/cell)
extrapolated 5 seeds (load+setup+sweep, sequential): ~58s total
```

1620 cells, single CPU process, well under a minute of compute. No numeric
resource budget is recorded elsewhere in the roadmap or ticket docs for
Phase E specifically (`CP2-T018` centralizes constants/paths, not a compute
budget) — this benchmark is the resource estimate. **No scope shrink
required** (ticket §12 blocking condition not triggered).

## 5. Execution plan

1. For each of the 5 paired (training_seed, poisoning_seed): load real
   collection, lock `mu_flag_threshold`, precompute `auroc_records` once.
2. For each of the 9 eligible victims × 3 policies × 3 sources × 4 fractions:
   run `run_mvp_cell`, compute blast radius + spillover, append one result
   row.
3. Assert no in-place mutation of the victim's clean calibration array for
   every cell (carried over from CP2-T043's verification approach).
4. Write `nbaiot_mvp_manifest.json` (run-level) and the aggregated results
   table.
5. Hand off to CP2-T045 (cleanup checkpoint) → CP2-T046 (manifest/result
   sanity audit) → CP2-T047 (kill triggers) → CP2-T048 (drift check) →
   CP2-T049 (CONTINUE/STOP/PIVOT decision).

## 6. Authorization

This plan is locked under **CP2-T044**, which is the Phase E bounded-MVP
authorization gate (governance fix, decision log 2026-06-16). It authorizes
exactly the 1620-cell matrix in §1 and nothing wider. Execution proceeds
immediately following this document per the user's standing instruction to
continue Phase E once the run plan is locked.
