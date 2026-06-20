# Code Quality Rules -- datp-cp

These rules apply to all implementation agents (Claude, Codex, Hermes backup) and to all code reviews (Codex, Claude, OpenClaw, Hermes).

No exceptions without a written justification in .rework/DECISIONS.md.

---

## 0. INSPECT .CLAUDE COMMANDS FIRST

Before implementing, both Claude and Codex must inspect .claude commands such as
/cleanCode or /cleanCodeCommit.

Extract useful clean-code rules from them.

Do not run any command that commits. If a command includes a commit step,
use only its non-commit checks manually.

---

## 1. ENUMS

Use strict enums for all closed vocabularies.

Every enum that represents a domain concept must be defined in one canonical location.

Enum members must be UPPER_CASE.

No string literals substituting for enum members in core logic.

No raw .value comparison in core logic; compare enum members directly.

Required enum domains:

    ExperimentStage        -- SYNTHETIC_SMOKE, NBAIOT_MAIN, CICIOT_STRETCH, FINAL_AUDIT
    ThresholdPolicy        -- GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD
    AttackerObjective      -- THRESHOLD_RAISE, THRESHOLD_LOWER
    PoisoningSourceStrategy -- RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN
    CalibrationInjectionRule -- REPLACE_FIXED_BUDGET
    PoisoningKnowledge     -- (as defined in roadmap)
    PoisoningTargetScope   -- (as defined in roadmap)
    PoisoningDefense       -- (as defined in roadmap)
    ExperimentScale        -- BOUNDED, FULL (domain words, not MVP)
    AuditDisposition       -- (as defined in roadmap)
    MetricName             -- if useful
    ArtifactKind           -- if useful
    RunStatus              -- if useful

Forbidden enum members (obsolete, must not exist):

    B0, B1, B2, B3, B4
    B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER
    NBAIOT_BOUNDED, NBAIOT_SMOKE (old naming)
    REGIME_A, REGIME_B, REGIME_C, REGIME_D
    MVP (as a member)

No backwards-compatible parsing that silently accepts old member names.

If an old member value arrives at a boundary, reject it with a clear validation error.

---

## 2. DATACLASSES

Preferred pattern:

    @dataclass(frozen=True, slots=True)

Use frozen dataclasses for all structured value types.

Required frozen dataclasses:

    run config
    clean artifact config
    poisoning config
    threshold config
    cluster config
    matrix plan
    run plan
    manifest records
    metric records
    audit findings
    command results
    paper artifact records
    reviewer findings

No raw dict used as a config, manifest, result, or plan in core logic.

No untyped list or tuple for structured data.

Boundary exception: deserialized JSON/YAML/TOML arrives as a dict only at the boundary.
Immediately validate and construct the appropriate frozen dataclass. Never pass the raw dict further.

---

## 3. TYPE PRECISION

Required:

    precise return types on all functions
    precise parameter types on all functions
    typed class fields
    typed module-level constants

Forbidden in core logic:

    Any (use a precise type or Union of precise types)
    object (use a precise type)
    Dict (use dict[K, V] or a dataclass)
    Mapping[str, Any] (use a dataclass)
    untyped list (use list[T])
    untyped tuple (use tuple[T, ...] or tuple[T1, T2, ...])
    Callable without type arguments
    Enum | str compatibility unions
    dataclass | str compatibility unions
    Path | str unions in core logic

No type: ignore without a comment explaining why it is unavoidable and tracking it.

---

## 4. NAMING RULES

Canonical project name in human-facing text: datp-cp

Python module/variable names: datp_cp

Class names: DatpCp*

Forbidden in production code (src/, tests/, artifact filenames, JSON field values):

    CP2, cp2, MVP, mvp, Phase E, PhaseE
    Ticket IDs (CP2-T044, FB1, etc.)
    Regime A/B/C/D, REGIME_A/B/C/D
    B0, B1, B2, B3, B4, B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER
    NBAIOT_BOUNDED, for_bounded_mvp
    run_regime_a/b/c, run_main_matrix (old names)
    legacy, compat, backward in identifiers

These terms may appear ONLY in .rework/ audit and history files where explicitly classified as obsolete.

---

## 5. HARDCODED VALUES

No scientific constants embedded in logic functions.

All scientific constants must be:

    named (UPPER_CASE constant name)
    typed (annotated with the correct Python type)
    defined in a designated constants module or config dataclass
    traceable to the roadmap via a brief comment

Required named constants:

    CALIBRATION_MIN_SAMPLES       -- n_min = 100
    TRAINING_SEEDS                -- [0, 1, 2, 3, 4]
    POISONING_SEEDS               -- [100, 101, 102, 103, 104]
    ANALYSIS_SEEDS                -- [300, 301, 302, 303, 304]
    CLUSTER_K_NBAIOT              -- 3
    CLUSTER_NINIT_NBAIOT          -- 10
    CLUSTER_MAX_ITER              -- 300
    CLUSTER_RANDOM_STATE          -- 42
    DEFAULT_FRACTION_GRID         -- [0.0, 0.10, 0.20, 0.40]
    FULL_FRACTION_EXTENSION       -- [0.05] (conditional, full scope only)
    CALIBRATION_POISONING_OUTPUT_ROOT -- artifact output root path

No magic numbers in algorithm bodies.

Artifact paths must be built from named constants, not inline strings.

---

## 6. DOCSTRINGS AND COMMENTS

Short technical docstrings are allowed.

Forbidden docstring patterns:

    "This module provides..."
    "This class is responsible for..."
    "Here we..."
    "The purpose of this function is..."
    restating the code in prose
    listing parameters with no additional information
    ticket IDs or phase labels in text
    AI-assistant filler language

Allowed comments:

    non-obvious scientific invariants
    reproducibility constraints
    numerical caveats
    reviewer-risk decisions

One-line docstrings for simple functions are acceptable if genuinely informative.

---

## 7. DEAD CODE AND IMPORTS

No stale imports.

No unused module-level variables.

No dead functions or classes.

No old wrappers kept for compatibility.

No redirect modules that only re-export from a new location.

No commented-out code blocks.

If code is removed, remove it entirely.

---

## 8. BOUNDARY DISCIPLINE

CLI/config/JSON/YAML input is untyped at the boundary only.

At the boundary:

    parse the raw input
    validate against expected values (raise a clear error on invalid input)
    construct the appropriate enum or frozen dataclass
    pass only the typed value into core logic

After the boundary, core logic must never receive raw strings, raw dicts, or unvalidated values.

Fail fast: if an obsolete value arrives, raise a ValueError with a message naming
the invalid value and the valid choices.

No silent fallback. No permissive parsing. No old-to-new translation maps.

---

## 9. GLOBAL STATE

No module-level mutable globals.

No mutable class-level state masquerading as a singleton.

No implicit shared mutable config.

Configuration must flow through explicit function parameters or dependency injection.

---

## 10. ENFORCEMENT

Ruff must pass: python -m ruff check src/ tests/

Pyright must pass: python -m pyright

Impacted tests must pass: python -m pytest <impacted>

Any violation not caught by ruff/pyright is a code review finding.

OpenClaw, Codex, Claude, and Hermes must flag violations even if ruff/pyright do not catch them.
