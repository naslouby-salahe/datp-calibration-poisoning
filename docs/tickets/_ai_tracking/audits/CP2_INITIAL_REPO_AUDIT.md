# CP2 Initial Repository Audit

**Date:** 2026-06-15
**Ticket:** CP2-T001 (read-only)
**Repo HEAD:** `0a5e380` (working tree clean)
**Verdict:** repository is a reusable DATP substrate with a **legacy CP2 prototype
that does not match the CP2 protocol**. No journal-comparator contamination in
attack/experiment code. CP2 protocol implementation is greenfield (Phases B–C).

> Read-only audit. No production code changed. Findings feed Phase A (T007–T015).

---

## 1. Method

```bash
ls src/datp; ls -la src/datp/attacks src/datp/experiments
cat src/datp/attacks/{calibration_poisoning,poisoning_config,poisoning_metrics}.py
cat src/datp/experiments/calibration_poisoning.py
rg -ni "edge-?iiot|fedprox|ditto|fedrep|fedper|laridi|fedstatsbenign|conformal|temporal recalibration" src
rg -ni "epochs *= *5|E=5" src
rg -ln "shift_magnitude|attack_rate" src
make help
```

## 2. Reusable DATP substrate (confirmed present)

`src/datp/` packages available for CP2 reuse:

```
attacks/  artifacts/  analyses/  app/  audit/  checkpointing/  conf/  config/
core/  data/  evaluation/  experiments/  federated/  modeling/  reporting/
scoring/  statistics/  testsupport/  thresholding/  validation/
```

The thresholding, scoring, statistics, evaluation, and reporting packages are the
intended DATP reuse base for CP2 (threshold derivation, score artifacts, CV(FPR),
bootstrap). Detailed reuse audit deferred to Phase A (T011–T012).

## 3. Legacy CP2 prototype — MISMATCH (primary finding)

Files: `src/datp/attacks/{calibration_poisoning,poisoning_config,poisoning_metrics}.py`
and `src/datp/experiments/calibration_poisoning.py`.

The prototype implements an **`attack_rate` + `shift_magnitude` add/subtract**
model:

- `poison_calibration_errors(...)` selects `n_poison = round(n·attack_rate)`
  positions and **adds/subtracts `shift_magnitude`** to the values.
- Enum is `PoisoningObjective.{RAISE_THRESHOLD, LOWER_THRESHOLD}`.
- Config field `shift_magnitude` (non-protocol).

This **does not match** the CP2 protocol, which requires:

- `REPLACE_FIXED_BUDGET`: `m_i = max(1, round(f·n_i))` positions **replaced** with
  values **resampled with replacement** from the **victim-local benign reservoir**
  (cardinality preserved, no value shifting/adding).
- Objectives `{THRESHOLD_RAISE, THRESHOLD_LOWER}` (naming differs from prototype).
- Sources `{RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}`.
- Fractions `{0, 0.10, 0.20, 0.40}`; no in-place mutation of clean arrays.

**Action:** the prototype is to be **retired/replaced** during Phase B/C (T016
enums, T017 config, T027 injector). `shift_magnitude` / `attack_rate` must be
removed. Detailed prototype audit is CP2-T010. No change in Phase 00 (read-only).

Positive note: the prototype already restricts baselines to `(B1, B2, B4)` —
**B3 is absent**, consistent with the CP2 default policy lock.

## 4. Forbidden-scope scan in `src/` — clean except one substrate flag

- **No** Edge-IIoTset, FedProx, Ditto, FedRep, FedPer, Laridi, B-FedStatsBenign,
  or "temporal recalibration" in `src/`.
- **No** `E=5` / `epochs = 5` literals in `src/`.
- **Flag (substrate, pre-existing):** `src/datp/thresholding/thresholds.py` defines
  `conformal_threshold(...)`. This is **DATP substrate**, not CP2 attack code. CP2
  forbids *conformal thresholding in CP2 scope*: CP2 policies `{B1, B2, B4}` must
  **not** be wired to conformal thresholds. Pre-existing DATP code is read-only in
  Phase 00; **carry this flag to CP2-T009 (journal/forbidden-scope audit)** and
  CP2-T011 (thresholding audit) to confirm CP2 does not consume it. Not a hard-stop.

## 5. Clean artifacts & E=1 / Graphify

- Clean-score artifact provenance and E=1 enforcement are **not** audited here;
  that is CP2-T007 (Phase A). No `E=5` artifacts found in code.
- Graphify is installed (`graphify 0.8.39`) and a graph exists under
  `graphify-out/` (built from commit `27c1dc31`). No `graphify` reference exists in
  `Makefile`/`COMMANDS.md`/`README.md`/`pyproject.toml`. Graphify workflow doc is
  CP2-T004.

## 6. Index impact

No finding invalidates `TICKET_INDEX.md`. The prototype mismatch is already
anticipated by CP2-T010 (prototype audit) and CP2-T016/T017/T027 (protocol
rebuild). The `conformal_threshold` substrate flag is already covered by the
CP2-T009/T011 audit scope.

## 7. Outcome

Acceptance met: audit reflects current reality; prototype mismatch and the
substrate `conformal_threshold` flag recorded; no divergence from the index that
requires re-planning. Read-only — no code changed.
