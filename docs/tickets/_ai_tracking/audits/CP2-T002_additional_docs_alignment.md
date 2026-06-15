# CP2-T002 — Additional_Docs Alignment Audit

**Date:** 2026-06-15
**Ticket:** CP2-T002 (read-only docs audit)
**Inputs:** `Additional_Docs/Synthesis/{Claims.md, Gap & Limitation Ledger.md,
Literature Matrix.md, State_of_the_Art.md}`, `Additional_Docs/Journal/
Journal_Extension_Master_Roadmap.md` (boundary only), `docs/DATP_CP_Roadmap.md`.
**Verdict:** CP2 scope aligns with the DATP reference docs; no journal scope is
imported; claim/limitation boundaries extracted to paper notes.

> Read-only. No code changed. No journal-scope features imported.

---

## 1. DATP conference identity → CP2 reuse map

| DATP conference element | CP2 reuse |
|---|---|
| N-BaIoT physical-device FL autoencoder (Rey-lineage, `Claims.md` P003) | Primary regime `REGIME_A_NBAIOT`; fixed encoder + shared per-client benign calibration scores |
| B1 (global) vs B2 (personalized) threshold policies; CV(FPR) dispersion | Core policy-differentiated comparison under poisoning |
| B4 (fingerprint cluster) threshold policy | Cluster-policy delta decomposition (`Δτ_agg + Δτ_churn`) |
| Train-once / derive-many; AUROC from unchanged test scores | Poisoning is the only stochastic variable; AUROC invariant |

CP2 adds exactly one new axis: **calibration-channel poisoning** of the per-client
benign calibration scores. Training, weights, aggregation, and test data are
untouched.

## 2. Claim / limitation boundaries (extracted)

- **Privacy gap is corpus-wide** (`Claims.md`: P001-C4, P002-C3, P003-C7, P004-C4,
  P034-C2, P035-C4, P039-C3, P040-C3 all lack formal privacy). → CP2 **must not**
  claim privacy/DP.
- **Hardware/deployment gaps** (P005, P036, P037, P040). → CP2 **must not** claim
  on-device/deployment results.
- **Model-poisoning robustness is a different threat** (P003-C4/C5, P036, P037). →
  CP2 **must not** be framed as broad FL robustness or generic poisoning.
- Reviewer-risk items (statistics unit, coverage, AUROC invariance, B4 indexing)
  carried into `CP2_PAPER_NOTES_CONSOLIDATED.md`.

## 3. CP2 / journal boundary (explicit)

`Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md` is a
**contamination-boundary reference only**. CP2 must NOT import:

- **Edge-IIoTset** (forbidden).
- **FedProx / Ditto / FedRep / FedPer / Laridi / B-FedStatsBenign** comparators.
- **Conformal thresholding** and **temporal recalibration**.
- CICIoT2023 is **stretch-only**, FB4-gated.

No conflict found between `docs/DATP_CP_Roadmap.md` and `Additional_Docs/` that
would warrant a hard-stop.

## 4. Outcome

Acceptance met: alignment note written; CP2/journal boundary explicit; paper notes
seeded in `_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md`.
