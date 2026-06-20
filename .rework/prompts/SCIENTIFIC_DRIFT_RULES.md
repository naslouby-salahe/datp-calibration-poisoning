# Scientific Drift Rules — datp-cp

These rules define the hard scientific boundary for datp-cp.

Any agent (Claude, Codex, OpenClaw, Hermes) that detects a violation must stop, report it, and block the violating change.

---

## 1. ATTACK SURFACE — HARD BOUNDARY

datp-cp is calibration-channel poisoning ONLY.

The one and only attack surface:

    benign threshold-calibration scores for eligible clients

The following must NEVER be altered by the poisoning mechanism:

    training data
    training labels
    model weights
    model gradients
    FedAvg aggregation procedure
    server aggregation code
    test scores
    test labels
    test data
    other clients' raw calibration data (cross-client contamination forbidden in main claims)

If any code path touches any of the above in a way motivated by the attack, it is a hard violation.

---

## 2. CLEAN ARRAY INVARIANT

Clean calibration arrays must never be mutated in place.

The poisoning function must always operate on a copy.

Pattern:

    poisoned = clean_scores.copy()
    # apply replacement to poisoned
    # clean_scores is never touched

Any in-place mutation of a clean array is a CRITICAL scientific violation.

---

## 3. INJECTION RULE

Canonical injection rule: REPLACE_FIXED_BUDGET

    m_i = max(1, round(f * n_i))    positions selected from the calibration array
    replaced with values resampled with replacement from the victim-local reservoir
    cardinality preserved: len(poisoned) == len(clean) == n_i

Forbidden injection patterns:

    appending to the calibration array (changes cardinality)
    inserting new values (changes cardinality)
    using test scores as reservoir values
    using training scores as reservoir values
    using another client's calibration scores as reservoir values for cross-client claims
    using a different budget rule without explicit roadmap justification

---

## 4. RESERVOIR RULES

Reservoirs must be victim-local benign calibration scores.

    one reservoir per victim client
    sourced from that client's own clean calibration set
    never from test data
    never from training data
    never from another client's data (for main claims)

Strategy enum governs which scores are selected as candidates:

    RANDOM_BENIGN    — uniform random sample from victim's calibration scores
    HIGH_SCORE_BENIGN — highest-scoring values from victim's calibration scores
    LOW_SCORE_BENIGN  — lowest-scoring values from victim's calibration scores

No strategy may pull values from outside the victim-local benign calibration set.

---

## 5. SEED SCHEME

Canonical seed scheme:

    numpy.random.SeedSequence([training_seed, poisoning_seed, client_id, scope_id])

Integer seed addition is forbidden:

    # FORBIDDEN
    seed = training_seed + poisoning_seed

    # REQUIRED
    rng = numpy.random.default_rng(
        numpy.random.SeedSequence([training_seed, poisoning_seed, client_id, scope_id])
    )

Any deviation from the SeedSequence scheme must be recorded in .rework/DECISIONS.md with a scientific justification.

---

## 6. PAIRED COMPARISON INVARIANT

Every clean-vs-poisoned comparison must be a paired comparison.

Each pair must share:

    training_seed     — same FL training run
    victim plan       — same victim client identity
    model checkpoint  — same trained model weights
    data split        — same client data partition
    test scores       — same pre-computed test reconstruction errors
    test labels       — same test ground truth

The poisoning seed is the ONLY stochastic difference between the clean and poisoned conditions.

Unpaired comparisons are not valid for causal attribution.

---

## 7. THRESHOLD POLICY RULES

Only these three policies exist:

    GLOBAL_THRESHOLD
    LOCAL_THRESHOLD
    CLUSTER_THRESHOLD

GLOBAL_THRESHOLD: recomputed from eligible clients' local thresholds using aggregation.

LOCAL_THRESHOLD: recomputed per client from that client's own calibration scores.

CLUSTER_THRESHOLD: recomputed using the fixed cluster procedure and client-effective thresholds.

Cluster delta comparisons must be client-indexed effective-threshold deltas.

Do NOT compare raw k-means cluster label IDs across runs. Cluster IDs may differ across seeds.

---

## 8. AUROC INVARIANT

AUROC must be invariant to calibration-channel poisoning.

Reason: test scores are computed from model weights and test data, neither of which is attacked.

If any code path changes AUROC as a result of calibration-channel poisoning, it is a CRITICAL scientific violation.

Always assert in tests: poisoned AUROC == clean AUROC (within float tolerance) for each paired run.

---

## 9. CALIBRATION-PENDING CLIENTS

Clients with fewer than CALIBRATION_MIN_SAMPLES (n_min = 100) benign calibration samples are Calibration-Pending.

Rules:

    Calibration-Pending clients receive the global fallback threshold.
    Calibration-Pending clients are excluded from CV(FPR), eligible victim sets, and B4 (CLUSTER_THRESHOLD) clustering.
    Coverage ratio must be reported alongside CV(FPR).

Do not silently skip Calibration-Pending clients without reporting coverage.

Do not include Calibration-Pending clients in eligible-only aggregation.

---

## 10. METRICS AND STATISTICS

Primary metric: CV(FPR) = std(FPR) / mean(FPR)

No epsilon denominator in CV(FPR).

Always report coverage ratio with CV(FPR).

AUROC must be invariant (see section 8).

Statistical comparison:

    Two-layer structure: per-victim paired deltas -> 5 seed-level aggregates -> bootstrap CI.
    Bootstrap CI is computed on the 5 seed-level aggregates, not on 45 individual victim-seed pairs.
    Do not treat 9 victims * 5 seeds as 45 independent samples.

Sign test is supporting evidence only (no standalone primary claim).

---

## 11. FORBIDDEN CLAIMS

The following claims must NEVER appear in code comments, docstrings, docs, reports, or the paper:

    model poisoning
    training poisoning
    gradient poisoning
    aggregation poisoning
    evasion attack
    privacy guarantee
    privacy attack
    deployment performance claim
    latency / memory / communication claim
    broad FL robustness claim
    secure federated learning claim
    protection against general poisoning

Any such claim is a CRITICAL scientific drift violation.

---

## 12. DATASET SCOPE

Primary dataset: N-BaIoT (NBAIOT_MAIN stage).

CICIoT2023: optional stretch (CICIOT_STRETCH stage), conditional on feasibility gate.

Edge-IIoTset: FORBIDDEN. Must not appear in any active code, config, or artifact.

Journal-extension datasets: out of scope for datp-cp. Must not contaminate datp-cp.

---

## 13. DRIFT DETECTION SEARCH

Hermes and Codex must run this search to detect scientific drift:

    grep -RIn \
      --exclude-dir=.git --exclude-dir=.venv --exclude-dir=outputs --exclude-dir=.rework \
      -iE "model.?poison|weight.?poison|gradient.?poison|train.?poison|aggregat.?poison|evasion|backdoor|privacy|deployment|latency|communication.?overhead|robust.?federat|secure.?federat|edge.iiot" .

Any hit is a potential CRITICAL finding.

Classify each hit:

    VIOLATION — active claim or code path that violates the boundary
    TEST_ONLY — appears only in a test that verifies the boundary is NOT violated
    COMMENT_HISTORICAL — in .rework/ or archived history only, not active claim
    FALSE_POSITIVE — explain why
