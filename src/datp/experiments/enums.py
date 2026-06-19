from __future__ import annotations

import enum


class ExperimentScale(enum.StrEnum):
    """Experiment execution scale gate."""

    SMOKE = "smoke"
    BOUNDED = "bounded"
    FULL = "full"
    STRETCH = "stretch"


class DiagnosticStep(enum.StrEnum):
    COMPOSE_CONFIG = "compose_config"
    VALIDATE_CONFIG = "validate_config"
    PREPARE_DATA = "prepare_data"
    SET_SEEDS = "set_seeds"
    FL_TRAINING = "fl_training"
    LOAD_SCORES = "load_scores"
    DERIVE_THRESHOLDS = "derive_thresholds"
    EVALUATE = "evaluate"
    WRITE_METRICS = "write_metrics"
    CONTINGENCY_DECISION = "contingency_decision"
    SUMMARY = "summary"


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
    RUN_B0 = "run_b0"
    SWEEP_COMPLETE = "sweep_complete"


class ContingencyDecision(enum.StrEnum):
    GO = "go"
    CONTINGENCY = "contingency"
