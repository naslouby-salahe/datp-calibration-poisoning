# Schema, Enum, Constant Skill

## Purpose

Use this skill to prevent scattered strings, scattered parameters, duplicated literals, untyped payloads, and unclear ownership.

DATP must remain typed, centralized, and easy to audit.

## Ownership Map

Use this ownership map for every new or existing value.

## Scientific Parameters

Belong in config.

Examples:

1. Threshold quantile.
2. Minimum calibration samples.
3. Seeds.
4. Dirichlet alpha values.
5. Round budgets.
6. Convergence thresholds.
7. Bootstrap resample counts.
8. Dataset feature counts.
9. Split ratios.
10. Model dimensions.
11. Batch size.
12. Learning rate.
13. Evaluation tolerances when scientifically meaningful.

Do not hardcode scientific parameters in source modules.

## Constants

Belong in constants modules when they are stable identifiers.

Examples:

1. Artifact filenames.
2. Directory names.
3. Manifest filenames.
4. Marker filenames.
5. Metric key strings.
6. Logger names.
7. CLI help text repeated across commands.
8. Column names.
9. Score column names.
10. Report filenames.
11. Plot filenames.
12. Table filenames.

Do not duplicate these strings locally.

## Enums

Belong in enum modules when values represent finite choices.

Examples:

1. Baseline.
2. Regime.
3. Stage.
4. Dataset.
5. Split.
6. Run status.
7. Ticket status.
8. Artifact type.
9. Metric family.
10. Audit verdict.
11. Human intervention status.
12. Calibration status.
13. Experiment phase.

Do not use loose strings for finite domain choices.

## Schemas and Typed Objects

Belong in schema/model modules when values represent structured payloads.

Examples:

1. Config models.
2. Result payloads.
3. Manifest payloads.
4. Metric bundles.
5. Threshold summaries.
6. Score manifests.
7. Dataset audit results.
8. Validation results.
9. Analysis requests.
10. Plot requests.
11. Report requests.
12. Ticket audit results.

Do not use untyped dictionaries when a payload crosses a module boundary.

## Path Ownership

Artifact paths must be constructed through path/helper modules.

Do not build paths manually with repeated strings.

Centralize:

1. Results paths.
2. Checkpoint paths.
3. Score paths.
4. Log paths.
5. Figure paths.
6. Table paths.
7. Report paths.
8. Manifest paths.
9. Console log paths.
10. Supplementary paths.

## CLI Ownership

CLI option strings, help text, defaults, and parsing behavior belong in CLI modules or CLI-specific constants.

Do not duplicate the same option text across commands.

If multiple commands share an option, centralize it.

## Logger Ownership

Repeated logger names must be constants or derived from module identity.

Do not duplicate logger-name strings across a module or package.

## Default Value Rule

Input/config model fields should be required unless a default is explicitly justified.

A default is allowed only if:

1. It is scientifically valid.
2. It is operationally valid.
3. It is centralized.
4. It is documented.
5. It is tested.
6. It does not hide missing input.
7. It does not change experimental meaning silently.

## Creation Procedure

Before creating a constant, enum, schema, config field, or typed object:

1. Search existing owners.
2. Identify the domain.
3. Reuse existing owner when possible.
4. Extend the existing owner when appropriate.
5. Create a new owner only when no correct owner exists.
6. Add or update tests.
7. Update imports.
8. Remove old loose strings or dictionaries.
9. Run quality checks.

## Anti-Patterns

Do not:

1. Create `constants.py` dumping grounds without domain grouping.
2. Create duplicate enums with overlapping values.
3. Store scientific parameters as constants.
4. Store finite domain choices as loose strings.
5. Pass untyped dictionaries through public functions.
6. Build artifact paths manually.
7. Add defaults to avoid changing call sites.
8. Duplicate CLI help text.
9. Duplicate metric keys.
10. Duplicate logger names.
11. Create utility functions that bypass existing typed objects.
12. Mix paper/report labels with metric keys unless they are explicitly the same domain.

## Required Report

When using this skill, report:

1. Values found.
2. Existing owners checked.
3. Owners reused.
4. Owners extended.
5. New owners created.
6. Loose strings removed.
7. Dictionaries replaced.
8. Defaults removed or justified.
9. Tests updated.
10. Remaining ownership risks.