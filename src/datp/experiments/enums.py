from __future__ import annotations

import enum


class SweepStep(enum.StrEnum):
    BUILD_MATRIX = "build_matrix"
    VALIDATE_MATRIX = "validate_matrix"
    CHECK_CHECKPOINT = "check_checkpoint"
    TRAIN_FL = "train_fl"
    LOAD_CAL_SCORES = "load_cal_scores"
    COMPUTE_ELIGIBILITY = "compute_eligibility"
    COMPUTE_TAU_GLOBAL = "compute_tau_global"
    INIT_SCORE_PROVIDER = "init_score_provider"
    DERIVE_THRESHOLD = "derive_threshold"
    EVALUATE = "evaluate"
    WRITE_METRICS = "write_metrics"
    SWEEP_COMPLETE = "sweep_complete"


class ContingencyDecision(enum.StrEnum):
    GO = "go"
    CONTINGENCY = "contingency"


class PolicyRunStatus(enum.StrEnum):
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"
