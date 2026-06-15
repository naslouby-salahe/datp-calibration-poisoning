# CP2 Consolidated Paper Notes

Single source for paper-writing notes accumulated across tickets. Tickets that
produce evidence relevant to the manuscript append here. The final paper ticket
(**CP2-T058**) consolidates and audits these notes against claim discipline.

> Claim discipline (from `docs/DATP_CP_Roadmap.md` §15). The verb **"shows"** is
> earned only after the primary endpoint is met (material `Δτ`, correct sign,
> linked to ≥1 downstream metric, ≥4/5 seed consistency, strict-majority of
> eligible victims). Never claim: first poisoning work in FL-IDS; B2 universally
> worst; broad FL/model robustness; privacy/DP guarantees; deployment readiness;
> raw-traffic realizability from score-level results; significance from tiny
> unpaired samples.

---

## Note template

```
### PN-NNNN — <topic> (ticket CP2-TXXX)
- Date:
- Claim enabled:
- Claim blocked / not yet supported:
- Limitation disclosed:
- Figure/table affected:
- Reviewer-risk relevance (see Roadmap §14):
- Do-not-claim reminder:
- Evidence path:
```

---

## Standing reminders

- Lead vocabulary: "per-device FPR disparity", "alarm-burden predictability",
  "operating-point disparity" — not "fairness".
- Raise narrative anchored on victim TPR/BA; lower narrative on worst-client FPR /
  `ΔCV(FPR)`.
- Always report coverage / eligibility alongside CV(FPR).
- AUROC invariance is the expected sanity check (threshold-only intervention).
- Score-level proxy + high-fraction with-replacement repetition must be disclosed
  as a limitation.

---

## Notes

### PN-0001 — Phase 00 Claim Boundaries (tickets CP2-T002, CP2-T006)
- Date: 2026-06-15
- Claim enabled: CP2 follows the DATP clean fixed-FedAvg, E=1,
  threshold-calibration protocol and N-BaIoT physical-device framing as the
  unattacked baseline context; all clean and poisoned runs are CP2-generated in
  this repository.
- Claim blocked / not yet supported: No CP2 result claim is enabled yet; no
  threshold shift, downstream harm, defense, or policy-vulnerability claim can be
  written before experiments and result audit.
- Limitation disclosed: CP2 must disclose score-level proxy abstraction,
  high-fraction with-replacement repetition, N-BaIoT size/age, 9-client primary
  regime, and no deployment validation.
- Figure/table affected: Future threat-model table, experiment-matrix table,
  claims/evidence table, and limitations.
- Reviewer-risk relevance (see Roadmap §14): Avoid "just data poisoning" by
  naming the calibration channel precisely; avoid AUROC confusion by framing
  AUROC invariance as expected for a threshold-only intervention.
- Do-not-claim reminder: Do not claim first FL-IDS poisoning work, broad
  training/model/aggregation robustness, privacy/DP, deployment readiness,
  Edge-IIoTset, FedProx/Ditto/FedRep/FedPer/Laridi/B-FedStatsBenign, conformal
  thresholding, temporal recalibration, or venue strategy.
- Evidence path:
  `docs/tickets/_ai_tracking/audits/CP2_ADDITIONAL_DOCS_ALIGNMENT_AUDIT.md`;
  `docs/tickets/_ai_tracking/audits/CP2_PHASE_00_DRIFT_AND_READINESS_AUDIT.md`.
