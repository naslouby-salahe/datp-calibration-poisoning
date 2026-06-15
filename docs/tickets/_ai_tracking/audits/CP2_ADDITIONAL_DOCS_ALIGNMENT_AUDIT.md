# CP2 Additional_Docs Alignment Audit

**Date:** 2026-06-15  
**Ticket:** CP2-T002  
**Purpose:** Map DATP and synthesis references to CP2 without importing journal
scope.

## Files Inspected

- `Additional_Docs/paper/DATP.pdf` via `pdftotext`
- `Additional_Docs/Synthesis/Claims.md`
- `Additional_Docs/Synthesis/Gap & Limitation Ledger.md`
- `Additional_Docs/Synthesis/Literature Matrix.md`
- `Additional_Docs/Synthesis/State_of_the_Art.md`
- `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md`
- `docs/DATP_CP_Roadmap.md`

## DATP Conference Identity Reusable by CP2

`DATP.pdf` confirms the CP1/DATP anchor that CP2 may reuse:

- Fixed FedAvg autoencoder, `E=1`, full participation.
- Same encoder, seeds, and per-client score artifacts reused across threshold
  policies.
- Primary N-BaIoT regime with 9 physical-device clients.
- Threshold policies include B1 shared/client-averaged, B2 per-client, B3
  family-mean, and B4 cluster-mean in the original DATP paper.
- Primary operating-point disparity metric is `CV(FPR) = sigma_FPR / mu_FPR`,
  with IQR and max-min FPR as guards.
- Calibration-pending rule: clients below `n_min=100` are excluded from
  dispersion metrics and receive the global fallback threshold.

CP2 may build on that clean threshold-calibration substrate but changes the
research question: DATP has no adversary; CP2 adds a calibration-channel-only
adversary.

## CP2 Boundary Derived from Additional_Docs

The synthesis files are useful as reviewer-risk context, not as CP2 scope.

Relevant boundaries:

- Privacy claims are repeatedly identified as under-supported in the literature.
  CP2 must not claim formal privacy, DP, secure aggregation, or deployment
  privacy guarantees.
- Deployment and hardware validation are recurring gaps. CP2 must not add or
  imply hardware, energy, latency, or field-deployment claims.
- Training-data poisoning, model poisoning, robust aggregation, backdoors, and
  evasion are literature threats but are not CP2's attack surface.
- Edge-IIoTset, FedProx, Ditto, FedRep, FedPer, Laridi-style comparators, and
  `B-FedStatsBenign` are journal-extension or literature contexts only and must
  not enter CP2.
- Conformal thresholding and temporal recalibration appear in archived journal
  planning context, not CP2.

## Journal Roadmap Boundary

`Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md` is explicitly
marked:

> ARCHIVED INPUT CONTEXT — NOT AN OPERATIONAL ROADMAP.

It contains venue strategy, Edge-IIoTset, FedProx/Ditto/FedRep/FedPer,
Laridi/`B-FedStatsBenign`, conformal thresholding, and temporal recalibration
plans. These are **not** CP2 instructions. Phase 00 did not modify or research
venue/deadline strategy.

## Reviewer-Risk Items CP2 Should Preserve

- Use "per-device FPR disparity", "alarm-burden predictability", and
  "operating-point disparity" rather than broad fairness language.
- For raise attacks, anchor interpretation on victim TPR/BA degradation.
- For lower attacks, anchor interpretation on worst-client FPR and `Delta
  CV(FPR)`.
- Treat AUROC invariance as a sanity check for threshold-only intervention, not
  as a failure.
- Disclose the score-level proxy and high-fraction with-replacement repetition.
- Do not frame CP2 as generic FL poisoning or as robustness beyond calibration
  channel contamination.

## Verdict

CP2 and journal scope are cleanly separable at setup. No conflict was found that
requires a decision record. CP2-T002 is **done** with this audit and the
consolidated paper-note entry.
