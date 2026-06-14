# DATP Invariant Check Skill

Use this skill whenever a task touches DATP science, experiment logic, datasets, baselines, thresholds, training, metrics, reporting, tickets, or manuscript claims.

The goal is to prove that the change preserves the DATP scientific contract.

---

## 1. Required Inputs

Before applying this skill, inspect:

1. Active `docs/journal/*.md`
2. Relevant tickets.
3. Relevant code.
4. Relevant tests.
5. Relevant artifacts.
6. Relevant manuscript text, if any.

Do not rely on memory.

Do not rely on archived roadmap context when active journal files disagree.

---

## 2. Core Invariant Checklist

Check these first:

| Invariant | Required answer |
|---|---|
| Is DATP still threshold-scope-only in the controlled ladder? | Yes |
| Are B1–B4 derived from shared scores where required? | Yes |
| Is training shared per controlled cell? | Yes |
| Does threshold/result code avoid training? | Yes |
| Does reporting avoid recomputation? | Yes |
| Are scientific parameters config-driven? | Yes |
| Is calibration-pending behavior preserved? | Yes |
| Is CV(FPR) reported with coverage ratio? | Yes |
| Are Regime statuses preserved? | Yes |
| Are stress tests outside the core ladder? | Yes |
| Are claims narrower than evidence? | Yes |

Any `No` is a blocking issue unless the user explicitly changed the scientific scope.

---

## 3. Baseline Checklist

### B1

Required:

1. One shared threshold.
2. Derived from eligible benign calibration thresholds.
3. Equal-client arithmetic mean unless explicitly named sensitivity variant.
4. No attack labels.
5. No retraining.

### B2

Required:

1. Per-client benign threshold.
2. Canonical p95 unless active config changes q.
3. Calibration-pending fallback to global threshold.
4. No attack labels.
5. No retraining.

### B3

Required:

1. Family labels from canonical taxonomy.
2. Family-level threshold from eligible clients.
3. Proper fallback for missing/pending clients.
4. Correct Regime A scope unless explicitly extended.

### B4

Required:

1. Fingerprint is `[mean, std, skew, p95]` over benign calibration errors.
2. Clustering uses eligible clients.
3. Pending clients excluded from clustering.
4. Pending clients use global fallback.
5. Not framed as privacy.
6. K value follows active journal plan.

### Comparators

Required:

1. FedProx is stress-test only.
2. Ditto name used only if faithful.
3. FedRep-AE/FedPer-AE fallback labeled honestly.
4. `B-FedStatsBenign` is benign-only and not faithful Laridi.
5. `B-LaridiFaithful` is anomaly-labeled and outside DATP's benign-only assumption.
6. FedBN remains rejected unless active plan changes.

---

## 4. Regime Checklist

| Regime | Required interpretation |
|---|---|
| Regime A | Confirmatory physical-device N-BaIoT anchor. |
| Regime B-a | CICIoT2023 file-level pseudo-client boundary condition. |
| Regime B-b | Conditional CICIoT2023 device-MAC or device-group repartition after feasibility. |
| Regime C | N-BaIoT Dirichlet severity sweep, supportive/exploratory. |
| Regime D | Conditional Edge-IIoTset external validation after feasibility. |

Reject any wording that makes:

1. Regime B-a physical-device evidence.
2. Regime C the primary claim.
3. Regime D unconditional.
4. Regime B-b valid without metadata evidence.

---

## 5. Stage Boundary Checklist

Verify the stage boundaries:

```text
prepare → score → threshold/result → report
```

Forbidden crossings:

1. Threshold module calls training.
2. Result module prepares data.
3. Reporting module recomputes scores.
4. Figure/table code recomputes metrics from raw data.
5. CLI command silently performs multiple scientific stages without clear naming.
6. Stored-score analysis retrains.
7. Stress-test training overwrites mainline outputs.

---

## 6. Metric Checklist

Required around CV(FPR):

1. Coverage ratio.
2. Eligible client count.
3. Pending client count when applicable.
4. Seed count.
5. Delta definition.
6. Bootstrap CI when required.
7. Detection-quality tradeoff context.
8. Lower-tail Macro-F1 or worst-client BA when available.

Reject:

1. CV(FPR) alone.
2. Accuracy-only summaries.
3. Missing coverage.
4. Unqualified five-seed inference.
5. Hiding Macro-F1 degradation.

---

## 7. Claim Checklist

Allowed:

```text
DATP reduces cross-client FPR dispersion under the tested fixed-encoder threshold-scope protocol.
```

Forbidden unless directly proven:

1. Global anomaly-detection superiority.
2. Universal personalization superiority.
3. Formal privacy.
4. Poisoning robustness.
5. Backdoor robustness.
6. Evasion robustness.
7. Concept drift handling.
8. Hardware validation.
9. Deployment readiness.
10. Communication-efficiency claim.
11. Superiority over anomaly-labeled thresholding methods.
12. CICIoT2023 file-level results as physical-device proof.

---

## 8. Required Output

Use this format:

```text
# DATP Invariant Check

Verdict:
Scope:
Files inspected:
Commands run:

## Baselines
B1:
B2:
B3:
B4:
Comparators:

## Regimes
Regime A:
Regime B-a:
Regime B-b:
Regime C:
Regime D:

## Stage Boundaries
Prepare:
Score:
Threshold/result:
Report:

## Metrics
CV(FPR):
Coverage:
Detection tradeoff:
Statistics:

## Claims
Allowed claims:
Rejected claims:
Required wording changes:

## Final Decision
Can proceed:
Can mark DONE:
Reason:
Invalidation rule:
```
