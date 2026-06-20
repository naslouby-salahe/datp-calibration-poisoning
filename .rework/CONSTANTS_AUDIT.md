# Constants Audit — datp-cp

Audit of all named constants and hardcoded values in src/datp/.

Goal: all scientific values must be named constants traceable to the roadmap. No magic numbers in logic.

---

## Verdict

Not yet audited.

---

## Required Named Constants

All of the following must exist as named, typed, documented constants:

    CALIBRATION_MIN_SAMPLES       — n_min = 100 (Calibration-Pending threshold)
    TRAINING_SEEDS                — list of training seeds [0, 1, 2, 3, 4]
    POISONING_SEEDS               — list of poisoning seeds [100, 101, 102, 103, 104]
    ANALYSIS_SEEDS                — list of analysis seeds [300, 301, 302, 303, 304]
    CLUSTER_K_NBAIOT              — K = 3 for N-BaIoT clustering
    CLUSTER_NINIT_NBAIOT          — n_init = 10
    CLUSTER_MAX_ITER              — max_iter = 300
    CLUSTER_RANDOM_STATE          — random_state = 42
    DEFAULT_FRACTION_GRID         — [0.0, 0.10, 0.20, 0.40]
    FULL_FRACTION_EXTENSION       — [0.05] (conditional, full scope only)
    CALIBRATION_POISONING_OUTPUT_ROOT — artifact output root path

---

## Findings

### Status: not yet audited

Agents: run a grep for magic numbers and hardcoded seeds in src/:

    grep -RIn --include="*.py" -E "[0-9]+\.[0-9]+" src/datp/ | grep -v "test\|#" | head -40
    grep -RIn --include="*.py" -E "seed\s*=\s*[0-9]|random_state\s*=\s*[0-9]" src/datp/
    grep -RIn --include="*.py" -E "n_min\s*=\s*[0-9]|min_samples\s*=\s*[0-9]" src/datp/

Write findings here and create CLAUDE tasks for violations.
