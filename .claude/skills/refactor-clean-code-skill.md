# Refactor Clean Code Skill

## Purpose

Use this skill to make DATP code simple, typed, centralized, readable, testable, and static-analysis clean.

## Core Principle

Do not only make code pass. Make the code belong in the right place, express the right domain concept, and stay easy to audit.

## Refactor Checklist

For every affected module, check:

1. Is the module still needed?
2. Does it have one clear responsibility?
3. Are functions small and cohesive?
4. Are names domain-specific?
5. Are argument lists short?
6. Are structured values typed?
7. Are constants centralized?
8. Are enums centralized?
9. Are config values centralized?
10. Are schemas centralized?
11. Are artifact paths centralized?
12. Are metric keys centralized?
13. Are utilities owned by the correct domain module?
14. Is test setup clear?
15. Are old compatibility paths removed?
16. Are static-analysis diagnostics fixed at the root?

## Complexity Reduction

When reducing complexity:

1. Split validation from computation.
2. Split computation from I/O.
3. Split I/O from reporting.
4. Split plotting from data preparation.
5. Split CLI parsing from business logic.
6. Replace nested branches with guard clauses.
7. Replace repeated branches with lookup tables when type-safe.
8. Replace string dispatch with enums.
9. Replace primitive argument groups with typed objects.
10. Extract helpers only when the helper has a meaningful domain name.

## Large Method Rule

A large method must be reduced unless all of the following are true:

1. The method is linear.
2. The method is clearer as a single method.
3. There is no repeated logic.
4. There is no nested complexity.
5. There is no mixed responsibility.
6. Static-analysis tools do not flag it.

Otherwise, extract meaningful helpers.

## Long Argument List Rule

A function should not accept many primitive arguments when the arguments represent a single concept.

Replace with typed objects such as:

1. `RunIdentity`
2. `DatasetIdentity`
3. `AnalysisRequest`
4. `ThresholdRequest`
5. `PlotRequest`
6. `ArtifactBundle`
7. `MetricBundle`
8. `AuditResult`
9. `ValidationResult`
10. `ReportBuildRequest`

Do not add default values just to make the object easier to instantiate.

## Naming Rule

Names must explain the domain role.

Avoid vague names such as:

1. `data`
2. `result`
3. `obj`
4. `item`
5. `tmp`
6. `val`
7. `thing`
8. `stuff`
9. `x`
10. `y`

Use names such as:

1. `client_thresholds`
2. `eligible_clients`
3. `calibration_errors`
4. `benign_scores`
5. `attack_scores`
6. `regime_alpha`
7. `run_identity`
8. `score_manifest`
9. `threshold_summary`
10. `coverage_ratio`

## Dead Code Rule

Delete dead code when:

1. It is not imported.
2. It is not tested.
3. It is not referenced by CLI.
4. It is not referenced by scripts.
5. It exists only for old compatibility.
6. It contradicts current tickets or scientific scope.
7. It causes diagnostics.

Do not keep dead code because it may be useful later.

## Duplication Rule

Remove duplication across:

1. Source code.
2. Tests.
3. CLI options.
4. Logger names.
5. Metric keys.
6. Artifact names.
7. Path fragments.
8. Baseline names.
9. Regime names.
10. Stage names.
11. Status names.
12. Plot labels.
13. Report labels.

Centralize repeated values in the correct owner.

## Suppression Rule

Diagnostic suppression is allowed only when all are true:

1. The diagnostic is a false positive.
2. The reason is documented locally.
3. The suppression is narrow.
4. The root cause cannot reasonably be fixed.
5. The quality gate accepts the explanation.

Blanket suppression is forbidden.

## Behavior Preservation

Before and after refactoring, verify:

1. Same ticket acceptance behavior.
2. Same scientific outputs where expected.
3. Same artifact paths where expected.
4. Same metric semantics.
5. Same config semantics.
6. Same deterministic seed behavior.
7. Same threshold-scope isolation.
8. Same shared-training invariant.

## Required Refactor Report

Report:

1. Refactor objective.
2. Files changed.
3. Complexity removed.
4. Duplication removed.
5. Dead code removed.
6. Constants centralized.
7. Enums centralized.
8. Config centralized.
9. Schemas introduced or reused.
10. Behavior-preservation evidence.
11. Tests run.
12. Remaining risks.