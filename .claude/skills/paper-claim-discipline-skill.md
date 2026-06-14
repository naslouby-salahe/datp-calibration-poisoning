# Paper Claim Discipline Skill

Use this skill for every manuscript, abstract, conclusion, caption, table title, README, report, audit, ticket, or documentation update that mentions DATP scientific findings.

The goal is to ensure every claim is narrower than the evidence.

---

## 1. Required Inputs

Before editing or auditing claims, inspect:

1. Active result artifacts.
2. Active `docs/journal/POST_EXPERIMENT_PLAN.md`.
3. Active `docs/journal/EXPERIMENT_PLAN.md`.
4. Relevant metrics files.
5. Relevant table and figure sidecars.
6. Relevant paper section.
7. Relevant ticket or audit report.

Do not update claims from memory.

Do not update claims from planned experiments.

Do not update claims before result freeze when the active plan forbids it.

---

## 2. Claim Evidence Levels

Classify every claim:

| Level | Meaning |
|---|---|
| `DIRECT` | Directly supported by DATP result artifacts under the stated protocol. |
| `SUPPORTIVE` | Supported by secondary regime, stress test, sensitivity, or mechanism analysis. |
| `BOUNDARY` | Shows where DATP does not improve or does not apply. |
| `EXPLORATORY` | Useful but not confirmatory. |
| `QUALITATIVE` | Literature- or design-based, not a DATP empirical result. |
| `FORBIDDEN` | Not supported and must be removed or rewritten. |

No claim may remain unclassified.

---

## 3. Core Claim Template

Preferred core wording:

```text
Under the tested fixed-FedAvg autoencoder protocol, device-aware per-client threshold calibration reduces cross-client FPR dispersion relative to a shared threshold in the Regime A N-BaIoT physical-device partition.
```

Acceptable shorter wording:

```text
DATP reduces FPR dispersion under the tested fixed-encoder threshold-calibration protocol.
```

Required qualifiers when relevant:

1. Tested protocol.
2. Fixed encoder.
3. Fixed training protocol.
4. Threshold calibration scope.
5. Regime A.
6. N-BaIoT physical-device partition.
7. Eligible clients.
8. Coverage ratio.
9. Seed count.
10. Detection-quality tradeoff.

---

## 4. Journal Claim Template

Preferred journal wording:

```text
The journal extension tests whether DATP's threshold-scope effect survives a stronger protocol with external validation, matched federated-threshold comparators, and stress tests, while preserving the fixed-encoder threshold-calibration identity.
```

Use only after the relevant experiments and result-freeze evidence exist.

Before result freeze, write:

```text
The journal extension is designed to test whether DATP's threshold-scope effect survives a stronger protocol...
```

Do not write outcome language before outcome evidence exists.

---

## 5. Required Claim Boundaries

### Regime A

Allowed:

```text
Confirmatory evidence.
```

Required:

1. Dataset.
2. Physical-device partition.
3. Seed count.
4. Coverage ratio.
5. B1 vs B2 delta.
6. Detection-quality tradeoff.

### Regime B-a

Allowed:

```text
Near-homogeneous boundary condition under file-level pseudo-clients.
```

Forbidden:

```text
Physical-device validation.
```

### Regime B-b

Allowed only after feasibility and results:

```text
Conditional device-MAC or device-group CICIoT2023 validation.
```

Forbidden before feasibility:

```text
CICIoT2023 device-level validation.
```

### Regime C

Allowed:

```text
Supportive severity-sweep evidence.
```

Forbidden:

```text
Primary confirmatory proof.
```

### Regime D

Allowed only after feasibility and results:

```text
External validation on Edge-IIoTset under the verified client partition.
```

Forbidden before feasibility:

```text
External device validation is confirmed.
```

---

## 6. Comparator Claim Boundaries

### FedProx

Allowed:

```text
Aggregation-side stress test.
```

Forbidden:

```text
Part of the same causal ladder as B1–B4.
```

### Ditto

Allowed only if faithful:

```text
Ditto stress test.
```

If not faithful, use:

```text
FedRep-AE/FedPer-AE fallback stress test.
```

Forbidden:

```text
Ditto-like custom method called Ditto.
```

### B-FedStatsBenign

Allowed:

```text
DATP-compatible benign-only federated-statistics threshold comparator.
```

Forbidden:

```text
Faithful Laridi reproduction.
```

### B-LaridiFaithful

Allowed only when implemented with anomaly-labeled summaries:

```text
Relaxed anomaly-labeled comparator outside DATP's benign-only calibration assumption.
```

Forbidden:

```text
DATP-compatible benign-only method.
```

---

## 7. Forbidden Claims

Remove or rewrite any claim that says or implies:

1. DATP is globally better at anomaly detection.
2. DATP is universally better than all thresholding methods.
3. DATP is formally privacy-preserving.
4. B4 preserves privacy.
5. DATP is robust to poisoning.
6. DATP is robust to backdoors.
7. DATP is robust to evasion.
8. DATP handles concept drift.
9. DATP is deployment-ready.
10. DATP is hardware validated.
11. DATP reduces communication cost.
12. DATP has production-grade runtime evidence.
13. CICIoT2023 file-level pseudo-clients are physical devices.
14. Regime C is confirmatory.
15. Stress tests are core baselines.
16. Five-seed bootstrap CIs are high-powered population inference.
17. Null or failed outcomes do not matter.
18. Dataset feasibility is obvious without evidence.
19. Post-hoc changes were pre-specified.
20. Conference and journal papers have no overlap.

---

## 8. Figure and Table Caption Rules

Every figure/table caption must identify:

1. Dataset or regime.
2. Baseline/comparator set.
3. Seed count.
4. Whether result is confirmatory, supportive, exploratory, boundary, or stress-test.
5. Metric definition when needed.
6. Coverage ratio when CV(FPR) is shown.
7. Whether shown result is illustrative or multi-seed.

Forbidden captions:

1. Captions claiming broad superiority.
2. Captions omitting regime.
3. Captions omitting illustrative-only status.
4. Captions calling stress tests core baselines.
5. Captions hiding null or mixed outcomes.
6. Captions that mismatch the visual type.

---

## 9. Abstract and Conclusion Rules

Update abstract and conclusion last.

Before editing abstract or conclusion, verify:

1. Result freeze passed.
2. Claim-survival wording selected.
3. Tables and figures finalized.
4. Limitations are explicit.
5. Null outcomes are disclosed.
6. Stress tests are scoped correctly.
7. Conference overlap disclosure is ready.
8. No forbidden claim remains.

The abstract must include limits if it includes results.

The conclusion must not be stronger than the results section.

---

## 10. Required Output

Use this format:

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
Can mark DONE:
Reason:
Invalidation rule:
```
