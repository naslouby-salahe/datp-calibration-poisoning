# Paper Claim Discipline Skill

> **datp-cp active.** Protocol of record: `docs/DATP_CP_Roadmap.md`.
> No backward compatibility by default. Tests: unit → integration (`tests/`).
> Forbidden: training/model/aggregation/test-data poisoning, Edge-IIoTset,
> conformal/temporal recalibration, journal-extension scope.
> Canonical policies: `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, `CLUSTER_THRESHOLD`.

Use this skill for every manuscript, abstract, conclusion, caption, table title, README, report, or documentation update that mentions datp-cp scientific findings.

The goal is to ensure every claim is narrower than the evidence. Protocol of record: `docs/DATP_CP_Roadmap.md`.

---

## 1. Required Inputs

Before editing or auditing claims, inspect:

1. Active result artifacts.
2. `docs/DATP_CP_Roadmap.md` §18 (Claims and Safe Wording) and §19 (Kill and Pivot Criteria).
3. Relevant metrics files.
4. Relevant table and figure sidecars.
5. Relevant paper section.

Do not update claims from memory.

Do not update claims from planned experiments.

Do not write outcome language before outcome evidence exists.

---

## 2. Claim Evidence Levels

Classify every claim:

| Level | Meaning |
|---|---|
| `DIRECT` | Directly supported by paired clean-vs-poisoned datp-cp result artifacts. |
| `SUPPORTIVE` | Supported by secondary analysis (cluster decomposition, diagnostic variants). |
| `BOUNDARY` | Shows where the attack does not apply or fails. |
| `EXPLORATORY` | Useful context but not confirmatory. |
| `QUALITATIVE` | Literature- or design-based, not an empirical datp-cp result. |
| `FORBIDDEN` | Not supported and must be removed or rewritten. |

No claim may remain unclassified.

---

## 3. Positive Result Wording (roadmap §18.1)

If the primary claim gate is met:

> datp-cp shows that poisoning only benign threshold-calibration data can materially shift threshold policies in federated IoT anomaly detection while training, aggregation, model parameters, and test data remain clean. Under the tested N-BaIoT setting, threshold-raising attacks degrade victim detection, threshold-lowering attacks degrade alarm-burden predictability, and global, local, and cluster threshold policies exhibit distinct vulnerability profiles.

---

## 4. Mixed Result Wording (roadmap §18.2)

> Under the tested N-BaIoT setting, calibration-channel poisoning produced bounded and policy-dependent effects. The observed harm was consistent for the supported objective or policy subset, while the remaining cells did not meet the pre-registered claim gate.

---

## 5. Negative Result Wording (roadmap §18.3)

> Under the tested gray-box score-level setting and poison fractions, calibration-only poisoning did not produce material, correctly signed threshold shifts with interpretable downstream movement. The result bounds this attack instantiation rather than proving general robustness of threshold calibration.

---

## 6. Required Claim Qualifiers

Every result claim must include:

1. Dataset: N-BaIoT.
2. Attack surface: calibration-channel only.
3. Fixed training: shared model parameters, aggregation, splits, and test data.
4. Threshold policy named explicitly.
5. Seed count (5 paired seeds).
6. Eligible client count and coverage.
7. Whether result is confirmatory (NBAIOT_MAIN), optional (NBAIOT_FULL_OPTIONAL), or diagnostic (STRETCH_DIAGNOSTIC_ONLY).

---

## 7. Forbidden Claims

Remove or rewrite any claim that says or implies:

1. Universal threshold vulnerability or universal robustness.
2. Raw-traffic attack realizability.
3. Broad FL robustness.
4. Formal privacy preservation.
5. Deployment readiness.
6. Robustness to poisoning, backdoors, or evasion.
7. Hardware validation.
8. Concept drift handling.
9. Training-data poisoning results.
10. Model-poisoning or aggregation-poisoning results.
11. Multi-client compromise from single-client data.
12. Results from diagnostic-only variants as main evidence.
13. Claims stronger than pre-registered primary claim gate.
14. Post-hoc changes presented as pre-specified.

---

## 8. Figure and Table Caption Rules

Every figure/table caption must identify:

1. Dataset or stage.
2. Policy or policy set.
3. Seed count.
4. Whether result is confirmatory, supportive, or diagnostic.
5. Metric definition when needed.
6. Coverage when CV(FPR) is shown.
7. Whether shown result is illustrative or multi-seed.

Forbidden captions:

1. Captions claiming broad superiority.
2. Captions omitting stage or policy.
3. Captions hiding null or mixed outcomes.
4. Captions that mismatch the visual type.

---

## 9. Abstract and Conclusion Rules

Update abstract and conclusion last.

Before editing abstract or conclusion, verify:

1. Result artifacts are frozen.
2. Claim-survival wording is selected.
3. Tables and figures are finalized.
4. Limitations are explicit.
5. Null outcomes are disclosed.
6. Diagnostic variants are clearly labeled.
7. No forbidden claim remains.

The abstract must include limits if it includes results.

The conclusion must not be stronger than the results section.

---

## 10. Required Output

```text
# Claim Discipline Audit

Verdict:
Scope:
Documents inspected:
Artifacts inspected:

## Claim Table
| Location | Claim | Evidence level | Verdict | Required change |
|---|---|---|---|---|

## Forbidden Claim Search
Terms checked:
Findings:
Fixes:

## Figure/Table Caption Check
Figures:
Tables:
Issues:
Fixes:

## Abstract/Conclusion Check
Abstract:
Conclusion:
Required limitations:

## Final Decision
Can publish/update:
Reason:
Invalidation rule:
```
