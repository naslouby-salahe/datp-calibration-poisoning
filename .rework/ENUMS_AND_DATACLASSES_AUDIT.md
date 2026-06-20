# Enums and Dataclasses Audit — datp-cp

Audit of all enum and dataclass definitions in src/datp/.

Goal: all closed vocabularies use strict enums; all structured configs and records use frozen dataclasses.

---

## Verdict

Not yet audited.

---

## Required Enums

Each enum must exist with exactly these members (no more, no fewer in the active set):

    ExperimentStage:
      SYNTHETIC_SMOKE
      NBAIOT_MAIN
      CICIOT_STRETCH
      FINAL_AUDIT

    ThresholdPolicy:
      GLOBAL_THRESHOLD
      LOCAL_THRESHOLD
      CLUSTER_THRESHOLD

    AttackerObjective:
      THRESHOLD_RAISE
      THRESHOLD_LOWER

    PoisoningSourceStrategy:
      RANDOM_BENIGN
      HIGH_SCORE_BENIGN
      LOW_SCORE_BENIGN

    CalibrationInjectionRule:
      REPLACE_FIXED_BUDGET

    ExperimentScale:
      BOUNDED
      FULL

Additional enums (verify members match roadmap):

    PoisoningKnowledge
    PoisoningTargetScope
    PoisoningDefense
    AuditDisposition

---

## Required Frozen Dataclasses

    CalibrationPoisoningConfig  — main experiment config
    VictimPlan                  — victim client specification
    BoundedSweepManifest        — manifest for a bounded sweep run
    PoisoningRunPlan            — single run parameters
    ExperimentResult            — result record for a single cell
    ArtifactDescriptor          — output path descriptor

---

## Forbidden Enum Members (must NOT exist in active enums)

    B0, B1, B2, B3, B4
    B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER
    NBAIOT_BOUNDED (old stage name)
    REGIME_A, REGIME_B, REGIME_C, REGIME_D
    MVP (as a member)
    COMMON, AUDIT_READONLY (old stage values)

---

## Findings

### Status: not yet audited

Agents: inspect src/datp/ for enum and dataclass definitions:

    grep -RIn --include="*.py" -E "class.*Enum\)|@dataclass" src/datp/

Write findings here and create CLAUDE tasks for violations.
