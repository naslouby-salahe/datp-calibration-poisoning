# Master Remediation, Refactoring, and Hardening Backlog

## 1. Scope, Evidence Boundary, and Planning Rules

This backlog is based exclusively on the four supplied inventory documents:

* `02 — Package Inventory`
* `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
* `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
* `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

No source-code behavior is treated as confirmed unless it is explicitly represented by those inventories. Any recommendation whose safety depends on runtime behavior, construction order, serialization details, public imports, Typer registration, artifact consumers, or actual import statements is explicitly verification-gated.

This is an incremental remediation program, not a rewrite plan.

The program preserves the following non-negotiable CP2 scientific and architectural boundaries:

* Calibration-channel poisoning only.
* No training-data poisoning.
* No model-update poisoning.
* No aggregation poisoning.
* No test-data poisoning.
* No backdoor, broad evasion, privacy, hardware, deployment, or journal-extension scope expansion.
* N-BaIoT remains the primary CP2 dataset.
* Clean-versus-poisoned comparisons remain paired.
* Poisoning remains the sole stochastic difference within a paired comparison.
* Inherited model, training, scoring, and test artifacts remain clean.
* Default CP2 threshold policies remain:

  * `B1_GLOBAL`
  * `B2_PERSONALIZED`
  * `B4_CLUSTER`
* `B3` remains excluded from the default CP2 policy set.
* B4 behavior, effective-threshold interpretation, deterministic parameters, and decomposition semantics remain reproducible.
* Seed semantics remain explicit, deterministic, and distinguishable by purpose.
* Existing artifact paths, manifests, output roots, lifecycle markers, metrics fields, and serialized outputs must not silently change.
* Scientific constants must not become casual editable runtime defaults.
* Generic DATP infrastructure and CP2-specific implementation must remain distinguishable.

The remediation program follows these planning rules:

1. One semantic concept receives one canonical owner.
2. Boundary models remain separate where they represent different responsibilities.
3. A repeated field is not automatically a defect.
4. A repeated numeric literal is not automatically the same semantic value.
5. A repeated file name is not automatically the same artifact contract.
6. A generic package must not become dependent on CP2 implementation details unless that dependency is explicitly justified.
7. CP2-specific behavior must not be generalized into generic infrastructure merely for stylistic consistency.
8. No new generic dumping-ground module may be introduced.
9. No artifact, manifest, configuration schema, CLI interface, or public import path may change silently.
10. Every code-changing ticket must finish with exactly three post-ticket audits before a dependent ticket starts.

---

## 2. Supplied Evidence Inventory

### 2.1 `02 — Package Inventory`

* Stated purpose:

  * Provides the repository package map, package responsibilities, module lists, static dependency observations, major classes, functions, enums, related tests, and selected package-level imports.

* Evidence type:

  * Package ownership.
  * Package directionality.
  * Module placement.
  * Static dependency observations.
  * Declared domain structures.
  * Test distribution.
  * Explicit empty package identification.

* Authority level:

  * Authority level: not established by the supplied materials.
  * It is the strongest supplied evidence for package topology and declared package-level dependencies.
  * Dependency observations must still be treated cautiously because the graph extraction is reported as partially inferred.

* Key constraints introduced:

  * `datp.core` is a leaf package with no internal `datp.*` imports.
  * `datp.artifacts` imports `datp.evaluation` and `datp.thresholding`.
  * `datp.scoring` imports `datp.artifacts`.
  * `datp.evaluation` imports `datp.scoring`.
  * `datp.reporting` imports `datp.attacks`.
  * `datp.analyses` is empty.
  * `datp.attacks` owns both scientific attack logic and CP2 manifests.
  * `datp.app.cli` contains several potentially overlapping command names.
  * `datp.testsupport` exists as a dedicated fixture and smoke-support package.

* Important evidence limitations:

  * The package graph is reported as 54% extracted and 46% inferred.
  * The inventory does not prove runtime circular imports.
  * The inventory does not prove public API status for module-level imports.
  * The inventory does not prove whether similarly named commands collide in Typer registration.

* Conflicts with other supplied documents:

  * No direct contradiction.
  * It provides package-level context for the type and constant duplication identified in the other inventories.

### 2.2 `03 — Methods, Functions, Inputs, Outputs, and Side Effects`

* Stated purpose:

  * Enumerates functions, key inputs, outputs, side effects, file I/O, scientific concepts, selected orchestration points, repeated input groups, and artifact layout methods.

* Evidence type:

  * Function signatures.
  * Side-effect boundaries.
  * File-read and file-write ownership.
  * Scientific computation boundaries.
  * Repeated parameter groups.
  * Path and manifest construction points.
  * CLI and orchestration entry points.

* Authority level:

  * Authority level: not established by the supplied materials.
  * It is the strongest supplied evidence for explicit function interfaces and declared side effects.

* Key constraints introduced:

  * `inject_fixed_budget` operates on copies and is intended not to mutate calibration arrays in place.
  * `build_reservoir` and `select_reservoir` operate on victim-local calibration data.
  * `recompute_pair` provides a policy-level threshold recomputation interface.
  * `compute_b4_pair` receives individual B4 scalar parameters.
  * `run_sweep_cell` receives multiple repeated CP2 identity parameters.
  * `run_nbaiot_bounded_sweep` writes a bounded-sweep manifest.
  * `run_logger` writes and reads JSON manifests.
  * Generic artifact I/O contains atomic JSON and CSV writers.
  * CP2 score loading reads Parquet score files.
  * `SweepCellSpec`, `CellId`, `SweepCellResult`, and `BoundedSweepResultRow` carry overlapping identity fields.

* Important evidence limitations:

  * The inventory does not confirm whether all listed functions are called from all possible paths.
  * The inventory does not prove whether private helper functions duplicate public behavior.
  * The inventory does not prove whether manifest assembly happens in one location or multiple locations.
  * The inventory does not prove external consumer expectations for function signatures.

* Conflicts with other supplied documents:

  * Supports the repeated-identity and B4-parameter concerns in `04` and `05`.
  * Supports the potential overlap between generic artifact I/O and CP2 manifest writers.

### 2.3 `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Stated purpose:

  * Enumerates existing enums, dataclasses, Pydantic models, constants, repeated structured data groups, and configuration defaults.

* Evidence type:

  * Canonical currently declared types.
  * Field-level overlap.
  * Enum vocabulary.
  * Constant ownership.
  * Configuration ownership.
  * Repeated scientific parameter groups.
  * Existing code-owned protocol values.

* Authority level:

  * Authority level: not established by the supplied materials.
  * It is the strongest supplied evidence for duplicated type, enum, and constant representations.

* Key constraints introduced:

  * CP2 policy vocabulary already exists in `ThresholdPolicy`.
  * CP2 source, target scope, objectives, defense, experiment scale, and injection-rule vocabulary already exist in `datp.core.poison_enums`.
  * `B3` is excluded from `ThresholdPolicy`.
  * B4 parameter values appear in:

    * `datp.artifacts.poison_names`
    * `datp.config.attack_config.B4ClusterConfig`
    * `datp.config.models.ThresholdConfig`
    * scalar parameters in `compute_b4_pair`
  * CP2 seed values appear in both constants and configuration-related models.
  * Repeated CP2 identity fields appear across path, sweep, result, and manifest models.
  * Generic artifact vocabulary and CP2 artifact vocabulary overlap around lifecycle markers.
  * Generic metric and payload vocabulary already exist in `datp.core.metric_enums`.

* Important evidence limitations:

  * The inventory does not establish which representation is currently used at runtime.
  * The inventory does not prove whether two fields with the same name have identical semantics.
  * The inventory does not prove whether values are immutable protocol locks or editable experiment settings.
  * The inventory does not prove whether historical artifact readers depend on specific aliases.

* Conflicts with other supplied documents:

  * It identifies repeated B4, seed, identity, and lifecycle representations that must be reconciled with the package map in `02` and side-effect inventory in `03`.

### 2.4 `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Stated purpose:

  * Identifies repeated numeric values, raw domain strings, path fragments, artifact names, manifest keys, local literals, and repeated validation or formatting patterns.

* Evidence type:

  * Literal duplication.
  * String-based enum drift risk.
  * Path-formatting repetition.
  * Scientific-value repetition.
  * Repeated protocol field groups.
  * Repeated configuration and dispatch patterns.

* Authority level:

  * Authority level: not established by the supplied materials.
  * It is advisory for duplication detection and must not be interpreted as proof that every repeated literal is semantically duplicate.

* Key constraints introduced:

  * `0.10`, `0.05`, `0.95`, `100`, and `42` occur in multiple distinct conceptual contexts.
  * Raw strings exist for:

    * threshold policies,
    * attack objectives,
    * poisoning target scopes,
    * datasets,
    * regimes,
    * baselines,
    * path prefixes,
    * score-column vocabulary.
  * CP2 path formatting includes:

    * `f"f_{fraction:.2f}"`
    * `"scope_{scope.value}"`
    * `"train_{seed}"`
    * `"poison_{seed}"`
  * Score schema vocabulary includes `"reconstruction_error"`.
  * Fraction validation appears in both `CellId.__post_init__` and guardrails.
  * CP2 path segments are constructed through multiple helper methods.

* Important evidence limitations:

  * Equal literals may represent different scientific concepts.
  * The inventory does not prove that all raw strings are used in runtime comparisons.
  * The inventory does not prove whether raw strings represent intentional serialized compatibility values.
  * The inventory does not prove whether path helpers are called from multiple locations.

* Conflicts with other supplied documents:

  * Reinforces the need for semantic classification before centralizing repeated values.
  * Does not justify merging values solely based on equality.

---

## 3. Binding Scientific, Experimental, and Architectural Contracts

### 3.1 CP2 Threat-Model Boundary

The remediation program must preserve the calibration-channel-only attack boundary.

The following must not be introduced or broadened incidentally:

* Training-data poisoning.
* Model-update poisoning.
* Aggregation poisoning.
* Test-data poisoning.
* Backdoor logic.
* General adversarial evasion workflows.
* Privacy mechanisms.
* Hardware profiling.
* Deployment simulation.
* Journal-extension datasets or comparators.
* New FL algorithms.
* New model architectures.
* New optimizer or aggregation strategies.
* New defense families beyond the explicitly inventoried trimmed-calibration defense.

### 3.2 Clean-versus-Poisoned Pairing Contract

Every future refactor affecting CP2 identity, manifests, seed pools, matrix enumeration, result rows, path construction, or reporting must preserve:

* The same training seed for clean and poisoned paired runs.
* The same victim or victim plan for clean and poisoned paired runs.
* The same clean inherited model and score artifacts.
* The same test data.
* The same policy parameters.
* The same B4 configuration.
* The same matrix conditions except for poisoning.
* Poisoning as the sole stochastic difference.

### 3.3 Policy Contract

The CP2 default policy set remains:

* `B1_GLOBAL`
* `B2_PERSONALIZED`
* `B4_CLUSTER`

The following remain binding:

* B3 must remain excluded from the default CP2 policy set.
* B1, B2, and B4 must remain scientifically distinct.
* B4 must not be simplified into a generic threshold formula.
* B4 raw cluster labels must not be treated as stable scientific identifiers.
* B4 comparisons remain client-effective-threshold comparisons.
* B4 decomposition must remain defined through:

  * clean effective threshold,
  * frozen-assignment aggregation component,
  * total poisoned effective threshold,
  * churn residual.

### 3.4 Scientific Parameter Contract

The following values are protocol-sensitive and require explicit ownership decisions before modification:

* `N_MIN`
* `TAIL_MASS`
* `MATERIALITY_FACTOR`
* `THRESHOLD_QUANTILE`
* `TRIM_FRACTION_PRIMARY`
* `TRIM_FRACTION_APPENDIX`
* `B4_K`
* `B4_N_INIT`
* `B4_MAX_ITER`
* `B4_RANDOM_STATE`
* `TRAINING_SEEDS`
* `POISONING_SEEDS`
* `ANALYSIS_SEEDS`
* `COMPROMISE_PATTERN_SEED`
* `BOUNDED_SWEEP_FRACTIONS`
* `FULL_SWEEP_FRACTIONS`
* `DEFAULT_POLICIES`
* `BOUNDED_SWEEP_OBJECTIVES`
* `BOUNDED_SWEEP_SOURCES`

Equal numeric values must remain semantically separate unless source verification proves identical ownership and meaning.

Examples that must not be consolidated merely because the literals match:

* `0.10` as tail mass.
* `0.10` as an attack fraction.
* `0.10` as an appendix trim fraction.
* `0.10` as a dataset split fraction.
* `0.05` as a full-grid fraction.
* `0.05` as a primary trim fraction.
* `0.95` as threshold quantile.
* `0.95` as statistical confidence level.
* `42` as B4 random state.
* `42` as a potentially unrelated bootstrap seed.

### 3.5 Artifact and Serialization Contract

The following are compatibility-sensitive by default:

* Existing output roots.
* `CALIBRATION_POISONING_OUTPUT_ROOT`.
* Artifact directory names.
* Manifest file names.
* Run file names.
* Marker file names.
* Path segment formats.
* Existing JSON keys.
* Existing CSV fields.
* Enum serialization values.
* Score schema vocabulary.
* Metric payload keys.
* Bounded-sweep manifest fields.
* Existing artifact discovery behavior.
* Existing resume and lifecycle semantics.

No ticket may alter any of those silently.

### 3.6 Package Direction Contract

The desired package direction is:

* `datp.core` remains low-level and free of high-level `datp.*` imports.
* `datp.data`, `datp.statistics`, and `datp.modeling` remain domain foundations.
* `datp.artifacts` should own names, paths, lifecycle, existence primitives, and transport I/O.
* `datp.scoring` should own persisted score schema and generic score loading/generation.
* `datp.evaluation` should own generic metric computation and generic metrics payload validation.
* `datp.thresholding` should own generic thresholding and eligibility behavior.
* `datp.attacks` should own CP2 attack logic and CP2-specific scientific behavior.
* `datp.reporting` should not absorb CP2 computation.
* `datp.app.cli` should remain a thin command boundary.
* `datp.testsupport` must remain test-only.
* `datp.analyses` must not become a generic dumping ground.

---

## 4. Consolidated Finding Disposition Register

### FND-001 — CP2 Condition and Run Identity Are Repeated Across Multiple Boundary Models

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * `SweepCellSpec`
  * `CellId`
  * `SweepCellResult`
  * `BoundedSweepResultRow`
  * `SeedRecord`
  * `run_sweep_cell`
  * `inject_single_victim`

* Concise finding:

  * CP2 identity fields are repeated across execution, path, result, and manifest representations.

* Disposition:

  * `OVERLAPPING`

* Root-cause identifier:

  * `RC-001`

* Canonical ticket identifier:

  * `TKT-004`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The models serve distinct boundaries and must not be collapsed into one giant model.
  * Their repeated field declarations create drift risk because the same semantic identity is manually represented in multiple locations.
  * The inventory does not establish whether `CellId` intentionally omits victim identity because paths aggregate victims or because identity is incomplete.

* Required future code verification:

  * Determine whether `CellId` is a victim-level, condition-level, or aggregate-directory identity.
  * Determine whether victim identity is encoded elsewhere in `PoisonLayout`.
  * Determine whether `SweepCellSpec` and `BoundedSweepResultRow` are independently constructed.

* Related findings:

  * `FND-006`
  * `FND-009`
  * `FND-016`

* Scientific or protocol sensitivity:

  * High.
  * Identity drift could break clean-versus-poisoned pairing or path uniqueness.

* Notes:

  * The correct target is a narrow canonical CP2 identity representation plus explicit projections, not a universal runtime/manifest/path model.

### FND-002 — CP2 Seed Pools Have Multiple Apparent Owners

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * `TRAINING_SEEDS`
  * `POISONING_SEEDS`
  * `ANALYSIS_SEEDS`
  * `COMPROMISE_PATTERN_SEED`
  * `SeedPools`
  * `DatpConfig.experiment.seeds`
  * `SeedRecord`
  * `SeedRecordModel`

* Concise finding:

  * Seed pools, seed derivation coordinates, and seed manifest projections are represented in separate locations without inventory-evidenced consistency enforcement.

* Disposition:

  * `OVERLAPPING`

* Root-cause identifier:

  * `RC-002`

* Canonical ticket identifier:

  * `TKT-002`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * Seed pools, derived seed coordinates, and persisted seed records are valid separate representations.
  * The likely concern is split ownership of seed-pool values rather than duplication of `SeedRecord` itself.

* Required future code verification:

  * Determine which CP2 code paths read constants directly.
  * Determine which paths consume `SeedPools`.
  * Determine whether generic `experiment.seeds` is shared with CP2 or unrelated.
  * Determine whether seed pools are persisted in one or more manifest schemas.

* Related findings:

  * `FND-004`
  * `FND-009`

* Scientific or protocol sensitivity:

  * High.
  * Seed drift could invalidate paired comparisons.

* Notes:

  * `SeedRecord` remains distinct from `SeedRecordModel`.

### FND-003 — B4 Parameters Have Four Separate Representations

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Source location:

  * `B4_K`
  * `B4_N_INIT`
  * `B4_MAX_ITER`
  * `B4_RANDOM_STATE`
  * `B4ClusterConfig`
  * `ThresholdConfig`
  * `compute_b4_pair`

* Concise finding:

  * B4 parameters are represented as constants, generic configuration fields, CP2 configuration fields, and scalar function parameters.

* Disposition:

  * `VALID_DEFECT`

* Root-cause identifier:

  * `RC-002`

* Canonical ticket identifier:

  * `TKT-003`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The inventory explicitly identifies the same B4 parameter group in four locations.
  * B4 behavior is protocol-sensitive and scalar parameter propagation creates drift risk.

* Required future code verification:

  * Determine whether `B4ClusterConfig` is already the runtime source.
  * Determine whether generic `ThresholdConfig` has different scope.
  * Determine whether values are serialized from config, constants, or function arguments.

* Related findings:

  * `FND-004`
  * `FND-014`

* Scientific or protocol sensitivity:

  * High.
  * B4 clustering reproducibility and decomposition semantics are at risk.

* Notes:

  * This does not authorize merging generic and CP2 B4 configurations without source verification.

### FND-004 — Scientific Protocol Values Are Split Across Constants, YAML Defaults, Config Models, and Function Defaults

* Source:

  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * `N_MIN`
  * `THRESHOLD_QUANTILE`
  * `TAIL_MASS`
  * trim fractions
  * seed tuples
  * YAML values
  * `ThresholdConfig`
  * `CalibrationPoisoningConfig`
  * function defaults

* Concise finding:

  * Scientific values appear in multiple potential ownership layers without inventory-evidenced enforcement of semantic consistency.

* Disposition:

  * `VALID_DEFECT`

* Root-cause identifier:

  * `RC-002`

* Canonical ticket identifier:

  * `TKT-002`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The inventory explicitly identifies duplicated defaults and matching values across code-owned constants and configuration.
  * The semantic equality of all occurrences remains unconfirmed, so classification is required before consolidation.

* Required future code verification:

  * Determine whether each repeated value is:

    * a protocol lock,
    * generic configuration,
    * CP2 configuration,
    * compatibility value,
    * local formatting value,
    * or coincidental literal equality.

* Related findings:

  * `FND-002`
  * `FND-003`
  * `FND-005`
  * `FND-019`

* Scientific or protocol sensitivity:

  * High.

* Notes:

  * The remediation must not move all constants into YAML.

### FND-005 — Matrix Definitions, Source-Objective Rules, and Guardrails Have Distributed Ownership

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Source location:

  * `DEFAULT_POLICIES`
  * `BOUNDED_SWEEP_OBJECTIVES`
  * `BOUNDED_SWEEP_SOURCES`
  * `BOUNDED_SWEEP_FRACTIONS`
  * `FULL_SWEEP_FRACTIONS`
  * `objective_for_source`
  * `assert_fractions_in_locked_grid`
  * `assert_policy_not_b3`
  * `enumerate_bounded_sweep_matrix`
  * `enumerate_full_sweep_matrix`

* Concise finding:

  * Matrix construction, allowed protocol vocabulary, source-objective mapping, and guardrails appear distributed across enum tuples, helpers, and matrix builders.

* Disposition:

  * `PARTIALLY_VALID`

* Root-cause identifier:

  * `RC-002`

* Canonical ticket identifier:

  * `TKT-002`

* Evidence strength:

  * Inventory-indicated.

* Why this disposition applies:

  * The inventory proves multiple relevant locations.
  * It does not prove that they disagree.
  * A source-verified shared protocol specification is justified only if matrix enumeration and guardrails are independently implemented.

* Required future code verification:

  * Determine whether `objective_for_source` is a mandatory mapping.
  * Determine whether `RANDOM_BENIGN` maps to no objective, one objective, or both objectives.
  * Determine whether bounded and full matrix logic intentionally differ.

* Related findings:

  * `FND-004`
  * `FND-014`
  * `FND-016`

* Scientific or protocol sensitivity:

  * High.

* Notes:

  * Bounded and full grids must remain distinct.

### FND-006 — Generic and CP2 Artifact Layouts Are Separate but CP2 Path Construction May Drift from CP2 Run Identity

* Source:

  * `02 — Package Inventory`
  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * `ArtifactLayout`
  * `PoisonLayout`
  * `CellId`
  * `CellPaths`
  * `_fraction_segment`
  * `_scope_segment`
  * `_training_seed_segment`
  * `_poisoning_seed_segment`
  * `_seed_segment`

* Concise finding:

  * Generic and CP2 layouts are correctly separated, but CP2 path construction relies on a separately declared path identity model that overlaps with execution and manifest identity.

* Disposition:

  * `PARTIALLY_VALID`

* Root-cause identifier:

  * `RC-003`

* Canonical ticket identifier:

  * `TKT-005`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * Keeping `ArtifactLayout` and `PoisonLayout` separate is supported.
  * The need to derive `CellId` from canonical CP2 identity is supported.
  * Whether victim identity is missing from path uniqueness requires source verification.

* Required future code verification:

  * Determine whether `PoisonLayout.run_dir` encodes victim identity directly or indirectly.
  * Determine whether distinct victim runs share paths.
  * Determine whether current directory structures are external compatibility boundaries.

* Related findings:

  * `FND-001`
  * `FND-007`
  * `FND-009`

* Scientific or protocol sensitivity:

  * High.

* Notes:

  * No universal artifact layout should be introduced.

### FND-007 — Lifecycle Marker Vocabulary Overlaps Across Generic and CP2 Artifact Enums

* Source:

  * `02 — Package Inventory`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * `ArtifactFile`
  * `RunFile`
  * `RunState`
  * `check_run_state`
  * `RunLifecycle`
  * `CellPaths.run_done`
  * `CellPaths.run_in_progress`

* Concise finding:

  * Generic and CP2 artifact vocabularies both define lifecycle concepts such as in-progress and done states.

* Disposition:

  * `OVERLAPPING`

* Root-cause identifier:

  * `RC-003`

* Canonical ticket identifier:

  * `TKT-005`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The inventory proves duplicated lifecycle terminology.
  * It does not prove that the markers have equal literal values or identical semantics.
  * The correct remediation is shared lifecycle interpretation with compatibility preservation, not automatic enum merging.

* Required future code verification:

  * Compare literal values.
  * Identify marker writer and reader ownership.
  * Determine whether CP2 uses generic `RunLifecycle`.
  * Determine whether abort and corruption states are represented in CP2 artifacts.

* Related findings:

  * `FND-006`
  * `FND-009`

* Scientific or protocol sensitivity:

  * Medium.
  * Lifecycle errors can compromise resume and artifact completeness.

* Notes:

  * CP2 payload file names remain CP2-owned.

### FND-008 — Runtime Results, Per-Run Manifests, Aggregate Sweep Manifests, and Provenance Models Need Explicit Conversion Boundaries

* Source:

  * `02 — Package Inventory`
  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Source location:

  * `SweepCellResult`
  * `PolicyPair`
  * `SingleVictimOutcome`
  * `MetricResult`
  * `FleetFprResult`
  * `DeltaTauResult`
  * `AurocRecord`
  * `B4ThresholdPair`
  * `B4DecompEntry`
  * `BoundedSweepResultRow`
  * `BoundedSweepManifest`
  * `RunManifest`
  * `ProvenanceRecord`
  * `SeedRecordModel`
  * `_row_for_cell`

* Concise finding:

  * Runtime and persisted CP2 representations are intentionally different but their explicit conversion ownership is not fully established by the inventories.

* Disposition:

  * `OVERLAPPING`

* Root-cause identifier:

  * `RC-003`

* Canonical ticket identifier:

  * `TKT-006`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The distinct models are valid boundary projections.
  * The inventory identifies a likely row-construction helper but does not prove it is the sole conversion path.
  * Explicit conversions and schema-level consistency checks are justified.

* Required future code verification:

  * Determine whether `_row_for_cell` is the only result-row assembler.
  * Determine whether manifests are assembled through multiple paths.
  * Determine whether Pydantic aliases, omitted fields, or null fields are compatibility-relevant.

* Related findings:

  * `FND-001`
  * `FND-007`
  * `FND-010`

* Scientific or protocol sensitivity:

  * High.
  * Persisted evidence must accurately represent paired computations.

### FND-009 — Generic Artifact Transport and CP2 Manifest Writing May Duplicate JSON Persistence Behavior

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `02 — Package Inventory`

* Source location:

  * `write_json_atomic`
  * `write_csv`
  * `write_metrics_atomic`
  * `emit_manifest`
  * `load_manifest`
  * `write_run_log_entry`
  * `write_nbaiot_bounded_sweep_manifest`

* Concise finding:

  * Generic artifact I/O and CP2 manifest writers both provide JSON persistence responsibilities.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-003`

* Canonical ticket identifier:

  * `TKT-006`

* Evidence strength:

  * Inventory-evidenced for overlapping roles; source verification required for actual duplication.

* Why this disposition applies:

  * The inventories prove multiple JSON-writing entry points.
  * They do not prove whether CP2 writers already delegate to generic atomic I/O.

* Required future code verification:

  * Determine whether CP2 writers use atomic transport.
  * Determine whether custom JSON encoding exists.
  * Determine whether JSON ordering matters to hashes, tests, or manifests.
  * Determine whether lifecycle marker transitions surround writes.

* Related findings:

  * `FND-008`
  * `FND-012`

* Scientific or protocol sensitivity:

  * Medium.

* Notes:

  * CP2 manifest schema logic must remain CP2-owned.

### FND-010 — Generic Score Loading and CP2 Score-Collection Loading May Duplicate Persisted Schema Interpretation

* Source:

  * `02 — Package Inventory`
  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * `datp.scoring.cal_loading`
  * `datp.scoring.loading`
  * `datp.scoring.schema`
  * `load_real_score_collection`
  * `ClientScores`
  * `ScoreCollection`
  * `SCORE_COLUMN`

* Concise finding:

  * Generic score-loading modules and CP2 real-score loading may both interpret score files and score-stage semantics.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-004`

* Canonical ticket identifier:

  * `TKT-007`

* Evidence strength:

  * Inventory-indicated.

* Why this disposition applies:

  * The inventory proves both generic and CP2 loading layers exist.
  * It does not prove duplicated parsing or schema validation.

* Required future code verification:

  * Determine whether CP2 loader delegates to generic loading.
  * Determine whether generic loading supports all CP2 stages.
  * Determine whether CP2 performs transformations unavailable in generic scoring.
  * Determine whether schema validation is duplicated.

* Related findings:

  * `FND-012`
  * `FND-015`

* Scientific or protocol sensitivity:

  * High.
  * Calibration/test separation must remain explicit.

### FND-011 — Static Package Dependencies Indicate a Potential Layering Cycle Around Artifacts, Evaluation, Scoring, and Thresholding

* Source:

  * `02 — Package Inventory`

* Source location:

  * Static dependency observations:

    * `artifacts -> evaluation`
    * `artifacts -> thresholding`
    * `evaluation -> scoring`
    * `scoring -> artifacts`
    * `thresholding -> evaluation`
    * `thresholding -> scoring`

* Concise finding:

  * The static package graph contains at least one potential cycle path:

    * `artifacts -> evaluation -> scoring -> artifacts`

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-004`

* Canonical ticket identifier:

  * `TKT-008`

* Evidence strength:

  * Inventory-evidenced for package-level graph direction.
  * Requires source verification before an actual circular import or runtime defect is claimed.

* Why this disposition applies:

  * The inventory does not prove runtime import execution order.
  * It does support a package-boundary cleanup investigation.

* Required future code verification:

  * Identify exact modules and symbols forming each path.
  * Determine whether imports occur at runtime or only in type checking.
  * Determine whether `results_exist` invokes metrics validation.
  * Determine whether scoring imports artifacts only for layout resolution.

* Related findings:

  * `FND-009`
  * `FND-017`

* Scientific or protocol sensitivity:

  * Medium.

* Notes:

  * Generic artifacts should not own metric semantics.

### FND-012 — Generic Reporting Imports CP2 Attacks

* Source:

  * `02 — Package Inventory`

* Source location:

  * `datp.reporting` imports `datp.attacks`.

* Concise finding:

  * A nominally generic reporting package depends on the CP2 attack package.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-004`

* Canonical ticket identifier:

  * `TKT-009`

* Evidence strength:

  * Inventory-evidenced for the package import.
  * Requires source verification for whether the dependency is legitimate result-model consumption or inappropriate computation coupling.

* Why this disposition applies:

  * Reporting may legitimately consume CP2 result models.
  * Reporting should not execute CP2 scientific logic or rely on mutable attack implementation details.

* Required future code verification:

  * Identify imported attack symbols.
  * Determine whether they are stable manifest types, runtime models, or computation functions.
  * Determine whether generic reporting has CP2-specific output paths.
  * Determine whether reporting can run without attack execution code imported.

* Related findings:

  * `FND-008`
  * `FND-016`

* Scientific or protocol sensitivity:

  * Medium.

### FND-013 — B1, B2, and B4 Implementations Are Intentionally Separate but Their Dispatch Boundary Needs Consolidation

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Source location:

  * `recompute_pair`
  * `_run_policy_pair`
  * `compute_b1_pair`
  * `compute_b2_pair`
  * `compute_b4_pair`
  * `B4ThresholdPair`
  * `ThresholdPolicy`

* Concise finding:

  * Multiple policy-specific recomputation functions are justified, but dispatch and validation ownership may be distributed.

* Disposition:

  * `PARTIALLY_VALID`

* Root-cause identifier:

  * `RC-005`

* Canonical ticket identifier:

  * `TKT-010`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * B1, B2, and B4 must remain separate.
  * The inventory establishes a public-looking `recompute_pair` dispatcher and an additional `_run_policy_pair` helper.
  * Source verification is required before concluding that dispatch is duplicated.

* Required future code verification:

  * Determine whether `_run_policy_pair` duplicates `recompute_pair`.
  * Determine whether policy branches are called elsewhere.
  * Determine whether B3 is rejected at all externally reachable policy boundaries.

* Related findings:

  * `FND-003`
  * `FND-005`
  * `FND-015`

* Scientific or protocol sensitivity:

  * High.

### FND-014 — Generic Evaluation and CP2 Metric Computation Have a Potentially Overlapping Boundary

* Source:

  * `02 — Package Inventory`
  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`

* Source location:

  * `datp.evaluation.metrics`
  * `datp.attacks.metric_engine`
  * `lock_mu_flag_threshold`
  * `compute_mu_flag_threshold`
  * `compute_metrics`
  * `compute_auroc_records`

* Concise finding:

  * Generic metrics and CP2 paired/delta metrics are appropriately separate in principle, but the boundary between generic formula reuse and CP2-specific computation is not fully established.

* Disposition:

  * `PARTIALLY_VALID`

* Root-cause identifier:

  * `RC-005`

* Canonical ticket identifier:

  * `TKT-010`

* Evidence strength:

  * Inventory-indicated.

* Why this disposition applies:

  * CP2 must retain delta tau, fleet FPR, AUROC invariance, blast radius, and spillover semantics.
  * Generic binary evaluation formulas should not be independently reimplemented unless scientifically justified.
  * The inventory does not prove formula duplication.

* Required future code verification:

  * Determine whether CP2 recomputes generic binary metrics.
  * Determine whether `lock_mu_flag_threshold` calls `compute_mu_flag_threshold`.
  * Determine whether AUROC is computed only from unchanged test scores.
  * Determine whether CP2 and generic metric fields have different meanings.

* Related findings:

  * `FND-013`
  * `FND-016`
  * `FND-017`

* Scientific or protocol sensitivity:

  * High.

### FND-015 — Bounded-Sweep Behavior Is Distributed Across Enumeration, Cell Execution, Run Orchestration, Persistence, and CLI

* Source:

  * `02 — Package Inventory`
  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`

* Source location:

  * `bounded_sweep_matrix`
  * `bounded_sweep_cell`
  * `bounded_sweep_run`
  * `cell_runner`
  * `run_nbaiot_bounded_sweep`
  * `run_bounded_sweep`

* Concise finding:

  * Bounded-sweep behavior is represented across several valid layers but requires explicit orchestration boundaries.

* Disposition:

  * `OVERLAPPING`

* Root-cause identifier:

  * `RC-006`

* Canonical ticket identifier:

  * `TKT-011`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * Matrix enumeration, single-cell scientific execution, aggregate orchestration, manifest persistence, and CLI routing are distinct responsibilities.
  * The inventory supports keeping them separate while clarifying ownership.

* Required future code verification:

  * Determine whether `run_sweep_cell` performs I/O.
  * Determine whether `run_nbaiot_bounded_sweep` writes per-cell artifacts or only aggregate manifests.
  * Determine whether dry-run and smoke commands use the same matrix and guardrails.

* Related findings:

  * `FND-001`
  * `FND-005`
  * `FND-008`
  * `FND-016`

* Scientific or protocol sensitivity:

  * High.

### FND-016 — CLI Commands Have Potentially Ambiguous Names and May Mix Command, Configuration, and Scientific Responsibilities

* Source:

  * `02 — Package Inventory`

* Source location:

  * `datp.app.cli.checkpoint_protocol`
  * `datp.app.cli.config`
  * `datp.app.cli.poison`
  * `datp.app.cli.report`
  * `datp.app.cli.status`
  * duplicate command names:

    * `preview`
    * `smoke`
    * `status`

* Concise finding:

  * CLI modules expose repeated command names and potentially overlap with orchestration responsibilities.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-006`

* Canonical ticket identifier:

  * `TKT-011`

* Evidence strength:

  * Inventory-evidenced for repeated internal function names.
  * Source verification required for actual CLI collision or leakage.

* Why this disposition applies:

  * Duplicate internal names are acceptable when registered in separate Typer groups.
  * CLI command naming and command registration cannot be inferred from the inventory alone.

* Required future code verification:

  * Determine Typer group registrations.
  * Determine whether command names are inferred or explicit.
  * Determine whether CLI modules directly build manifests, paths, matrices, or protocol configuration.

* Related findings:

  * `FND-015`
  * `FND-017`

* Scientific or protocol sensitivity:

  * Medium.

### FND-017 — Validation Responsibilities Appear Distributed Across Artifacts, Evaluation, Validation, Checkpointing, and Reporting

* Source:

  * `02 — Package Inventory`
  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`

* Source location:

  * `results_exist`
  * `validate_metrics_payload`
  * `datp.validation`
  * `datp.checkpointing.invariants`
  * `datp.reporting.validation`
  * `provenance_gate`
  * `metric_reproducer`
  * `score_manifest`

* Concise finding:

  * Multiple packages contain validation-related responsibilities without an inventory-evidenced scope map.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-004`

* Canonical ticket identifier:

  * `TKT-011`

* Evidence strength:

  * Inventory-indicated.

* Why this disposition applies:

  * Multiple validation layers can be legitimate if their scopes differ.
  * The inventory does not prove duplicate checks or conflicting verdicts.

* Required future code verification:

  * Determine validation scope for each function and module.
  * Determine whether `results_exist` performs semantic validation.
  * Determine whether reporting validation duplicates experiment validation.
  * Determine whether checkpoint validation overlaps with convergence validation.

* Related findings:

  * `FND-011`
  * `FND-014`
  * `FND-015`

* Scientific or protocol sensitivity:

  * High for provenance and paired-result validation.

### FND-018 — Test-Support Ownership Is Present but Potential Fixture Duplication Requires a Controlled Consolidation Review

* Source:

  * `02 — Package Inventory`

* Source location:

  * `datp.testsupport`
  * attack tests
  * checkpoint tests
  * core architecture tests
  * validation tests
  * artifact tests

* Concise finding:

  * The repository already has test-support utilities, but the inventory cannot establish whether equivalent local fixtures are duplicated elsewhere.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-007`

* Canonical ticket identifier:

  * `TKT-012`

* Evidence strength:

  * Inventory-indicated.

* Why this disposition applies:

  * Dedicated `testsupport` helpers exist.
  * Their existence does not prove duplicate fixtures.
  * Runtime import misuse and test duplication require source inspection.

* Required future code verification:

  * Identify local fixtures that construct equivalent synthetic score cases.
  * Determine whether runtime packages import `datp.testsupport`.
  * Determine whether architecture tests assert semantics or incidental module locations.

* Related findings:

  * `FND-020`
  * `FND-021`

* Scientific or protocol sensitivity:

  * Medium.

### FND-019 — Raw Domain Strings and Formatting Literals Need Boundary-Specific Canonicalization

* Source:

  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`
  * `05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory`

* Source location:

  * raw policy strings
  * raw objective strings
  * raw target-scope strings
  * raw dataset and regime values
  * path segment literals
  * `SCORE_COLUMN = "reconstruction_error"`

* Concise finding:

  * Existing enums cover several domain values that also appear as raw strings, while path and schema literals are valid compatibility boundaries.

* Disposition:

  * `PARTIALLY_VALID`

* Root-cause identifier:

  * `RC-002`

* Canonical ticket identifier:

  * `TKT-002`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * Internal raw-string comparisons should use canonical enums where appropriate.
  * Serialized forms, YAML values, CLI tokens, path segments, and schema column names must remain stable boundary representations.

* Required future code verification:

  * Determine which strings are internal comparisons.
  * Determine which strings are persisted compatibility values.
  * Determine whether aliases are supported.
  * Determine whether short baseline labels and long policy labels have distinct meanings.

* Related findings:

  * `FND-004`
  * `FND-006`

* Scientific or protocol sensitivity:

  * Medium.

### FND-020 — `datp.analyses` Is Explicitly Empty and Has No Evidenced Responsibility

* Source:

  * `02 — Package Inventory`

* Source location:

  * `datp.analyses.__init__.py`

* Concise finding:

  * `datp.analyses` is empty except for `from __future__ import annotations`.

* Disposition:

  * `NEEDS_CODE_VERIFICATION`

* Root-cause identifier:

  * `RC-007`

* Canonical ticket identifier:

  * `TKT-012`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The package is empty.
  * The inventory does not establish whether it is imported externally, reserved for future API use, or referenced in package metadata.

* Required future code verification:

  * Search source, tests, packaging metadata, CLI registration, and documentation references.
  * Determine whether the package is public compatibility surface.

* Related findings:

  * `FND-018`
  * `FND-021`

* Scientific or protocol sensitivity:

  * Low.

### FND-021 — `datp.core` Is Broad but Its Leaf-Layer Structure Is Inventory-Supported

* Source:

  * `02 — Package Inventory`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Source location:

  * `datp.core`
  * `datp.core.enums`
  * `datp.core.metric_enums`
  * `datp.core.poison_enums`
  * `datp.core.types`
  * `datp.core.identity`
  * `datp.core.seed_sequence`
  * `datp.core.provenance`

* Concise finding:

  * `datp.core` owns many concepts, but its leaf direction and internal module subdivision are already intentional and structurally valuable.

* Disposition:

  * `ALREADY_ADDRESSED`

* Root-cause identifier:

  * `RC-007`

* Canonical ticket identifier:

  * `TKT-012`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The inventory explicitly states that `datp.core` has no internal `datp.*` imports and is imported by all other packages.
  * Its responsibilities are separated into focused modules rather than one undifferentiated core file.
  * No broad package split is justified from inventory evidence.

* Required future code verification:

  * Determine whether high-level imports enter core indirectly.
  * Determine whether core re-exports create unexpected public compatibility obligations.
  * Determine whether CP2-specific enums and types can remain low-level shared primitives without coupling core to high-level packages.

* Related findings:

  * `FND-003`
  * `FND-019`
  * `FND-020`

* Scientific or protocol sensitivity:

  * Low.

### FND-022 — Generic Training Identity and CP2 Attack Identity Must Remain Separate

* Source:

  * `03 — Methods, Functions, Inputs, Outputs, and Side Effects`
  * `04 — Enums, Dataclasses, Constants, and Configuration Inventory`

* Source location:

  * `TrainingCellId`
  * `BaselineRunId`
  * `CellId`
  * `SweepCellSpec`
  * `SeedRecord`

* Concise finding:

  * Generic training identity and CP2 attack identity overlap around seeds but represent different lifecycles.

* Disposition:

  * `DOCUMENTATION_ONLY`

* Root-cause identifier:

  * `RC-001`

* Canonical ticket identifier:

  * `TKT-004`

* Evidence strength:

  * Inventory-evidenced.

* Why this disposition applies:

  * The inventories support separate lifecycle semantics:

    * training identity,
    * baseline identity,
    * attack condition identity,
    * attack execution identity,
    * seed derivation identity.
  * There is no evidence supporting a merge.

* Required future code verification:

  * Confirm how CP2 references inherited training artifacts.
  * Confirm whether provenance already links CP2 runs to `TrainingCellId`.

* Related findings:

  * `FND-001`
  * `FND-002`
  * `FND-006`

* Scientific or protocol sensitivity:

  * High.

---

## 5. Root-Cause Consolidation and Change-Impact Map

### RC-001 — CP2 Identity Has No Explicit Canonical Semantic Layer

* Root cause:

  * CP2 condition, execution, path, result, seed, and manifest representations share overlapping fields but lack an inventory-evidenced canonical semantic identity object.

* Findings consolidated:

  * `FND-001`
  * `FND-006`
  * `FND-008`
  * `FND-015`
  * `FND-022`

* Evidence:

  * `SweepCellSpec`, `CellId`, `SweepCellResult`, and `BoundedSweepResultRow` repeat policy, source, fraction, target scope, seeds, and related CP2 fields.
  * `CellId` and `SweepCellSpec` contain overlapping but not identical field sets.

* Why these findings belong together:

  * They all risk divergence between what a CP2 run means, how it is enumerated, where it is stored, and how it is recorded.

* Conceptual ownership:

  * A narrow CP2 identity module should own semantic condition identity and execution identity.
  * Existing models remain boundary projections.

* Affected conceptual areas:

  * CP2 matrix enumeration.
  * Attack execution.
  * Artifact paths.
  * Manifest rows.
  * Provenance.
  * Resume behavior.
  * Result grouping.
  * Reporting inputs.

* Configuration impact:

  * CP2 identity must receive typed policy, source, objective, fraction, scope, dataset, scale, and seed values from canonical configuration and enum owners.

* Enum impact:

  * Identity must use canonical enum values, not raw string duplicates.

* Dataclass impact:

  * `SweepCellSpec`, `CellId`, and `SweepCellResult` remain separate but must derive or validate against canonical identity.

* Constant/raw-string impact:

  * Path segment formatting remains a boundary projection.
  * Fraction formatting remains stable.

* Validation impact:

  * Identity-to-path, identity-to-manifest, and result-to-row validation become explicit.

* CLI or public-interface impact:

  * CLI must not construct CP2 identity from ad hoc raw values after canonicalization.

* Artifact and manifest impact:

  * Path uniqueness and manifest row uniqueness require explicit checks.

* Serialization impact:

  * Existing flat manifest fields remain stable.

* Result-loading and reporting impact:

  * Report loaders must consume normalized persisted identity fields.

* Test impact:

  * Identity equality, conversion, path uniqueness, pairing, and round-trip tests are required.

* Documentation impact:

  * CP2 identity vocabulary must distinguish:

    * condition,
    * run,
    * victim plan,
    * seed derivation record,
    * path projection,
    * result row.

* Reproducibility impact:

  * High.
  * Identity drift can invalidate pairing.

* Scientific or protocol impact:

  * High.

* Upstream dependencies:

  * Canonical enums.
  * CP2 protocol configuration.
  * seed pools.

* Downstream consequences:

  * Paths, manifests, reports, resume logic, aggregation, and diagnostics.

* Risks of partial implementation:

  * A new identity object introduced without replacing independent manual construction would increase duplication rather than reduce it.

* Canonical tickets:

  * `TKT-004`
  * `TKT-005`
  * `TKT-006`
  * `TKT-011`

### RC-002 — CP2 Protocol Locks Are Distributed Across Constants, Config, Enums, Helpers, and Function Defaults

* Root cause:

  * Scientific values and allowed CP2 condition sets are represented in multiple locations without an established one-way ownership and validation model.

* Findings consolidated:

  * `FND-002`
  * `FND-003`
  * `FND-004`
  * `FND-005`
  * `FND-019`

* Evidence:

  * Seed pools appear in constants and configuration.
  * B4 parameters appear in four locations.
  * threshold quantile and `N_MIN` appear in constants and configuration.
  * matrix tuples, source-objective helpers, and guardrails are distributed.
  * enum values coexist with raw strings.

* Why these findings belong together:

  * They all concern the absence of a clearly defined CP2 protocol-value ownership chain.

* Conceptual ownership:

  * `datp.core.poison_enums` or a successor domain enum module owns closed vocabulary.
  * `datp.config.attack_config` owns typed CP2 protocol configuration and effective configuration.
  * `datp.artifacts.poison_names` owns artifact names and output-root compatibility vocabulary.
  * Generic configuration remains in `datp.config.models`.

* Affected conceptual areas:

  * Seeds.
  * B4 configuration.
  * threshold quantile.
  * eligibility threshold.
  * tail mass.
  * trim fractions.
  * policy collections.
  * fractions.
  * objectives.
  * source strategies.
  * target scopes.

* Configuration impact:

  * The effective CP2 configuration must be serializable and validated.
  * Generic configuration and CP2 configuration must not silently compete.

* Enum impact:

  * Internal control flow should use enum values.
  * Boundary serialization retains existing strings.

* Dataclass impact:

  * `SeedPools` and `B4ClusterConfig` need clear scope boundaries.

* Constant/raw-string impact:

  * Every repeated value must be classified before consolidation.

* Validation impact:

  * Effective config must be checked against protocol locks.
  * Matrix enumeration and guardrails must consume the same approved condition definitions.

* CLI or public-interface impact:

  * CLI must report effective CP2 configuration rather than invent defaults.

* Artifact and manifest impact:

  * Resolved effective scientific values must be represented in manifests where required.

* Serialization impact:

  * Existing serialized values remain stable.

* Result-loading and reporting impact:

  * Reporting must interpret policy and metric values through canonical vocabulary.

* Test impact:

  * Default equivalence, mismatch rejection, matrix equivalence, enum serialization, and seed determinism tests are mandatory.

* Documentation impact:

  * Protocol locks must be labeled as:

    * immutable protocol lock,
    * generic configuration,
    * CP2 typed configuration,
    * compatibility constant,
    * derived representation.

* Reproducibility impact:

  * High.

* Scientific or protocol impact:

  * High.

* Upstream dependencies:

  * None beyond behavioral lock tests.

* Downstream consequences:

  * B4 recomputation, matrix enumeration, guardrails, manifests, CLI, reporting, and tests.

* Risks of partial implementation:

  * Moving only constants or only YAML defaults can create a third conflicting source of truth.

* Canonical tickets:

  * `TKT-002`
  * `TKT-003`
  * `TKT-010`

### RC-003 — CP2 Artifact Lifecycle, Layout, Manifest, and Transport Boundaries Are Not Fully Canonicalized

* Root cause:

  * CP2 artifacts use a valid separate layout family but lifecycle terminology, path construction, manifest assembly, and JSON transport appear distributed across multiple modules.

* Findings consolidated:

  * `FND-006`
  * `FND-007`
  * `FND-008`
  * `FND-009`

* Evidence:

  * Generic and CP2 path layouts coexist.
  * Generic and CP2 lifecycle terms overlap.
  * CP2 runtime and persisted models overlap.
  * Generic artifact I/O and CP2 manifest writers both write JSON.

* Why these findings belong together:

  * All concern how CP2 scientific results become persistent artifacts and how artifacts are later interpreted.

* Conceptual ownership:

  * Generic artifact transport belongs to `datp.artifacts.io`.
  * Generic lifecycle interpretation belongs to `datp.artifacts.lifecycle`.
  * CP2 payload names remain in `datp.artifacts.poison_names`.
  * CP2 manifest schemas remain CP2-owned.
  * CP2 result-to-manifest conversions receive explicit ownership.

* Affected conceptual areas:

  * output directories.
  * marker files.
  * manifests.
  * provenance.
  * resume behavior.
  * corrupt-state detection.
  * report inputs.
  * artifact discovery.

* Configuration impact:

  * Effective configuration must be recorded through schema-owned manifest fields rather than ad hoc payloads.

* Enum impact:

  * Lifecycle state and payload-file vocabulary must remain distinguishable.

* Dataclass impact:

  * `CellPaths`, `BoundedSweepManifest`, `RunManifest`, and provenance models require explicit conversion boundaries.

* Constant/raw-string impact:

  * Marker and file names remain compatibility values.

* Validation impact:

  * Artifact completeness, partial-run detection, marker consistency, row uniqueness, and schema validation become explicit.

* CLI or public-interface impact:

  * Status and resume commands must consume canonical lifecycle results.

* Artifact and manifest impact:

  * High.

* Serialization impact:

  * Existing schemas remain stable by default.

* Result-loading and reporting impact:

  * Readers must accept current and migrated artifacts if compatibility changes are authorized.

* Test impact:

  * Artifact path snapshots, lifecycle state matrix tests, manifest round trips, corrupt-artifact tests, and atomic-write tests.

* Documentation impact:

  * Artifact lifecycle meaning must be documented precisely.

* Reproducibility impact:

  * High.

* Scientific or protocol impact:

  * High.

* Upstream dependencies:

  * Canonical CP2 identity.
  * protocol configuration.

* Downstream consequences:

  * resume safety.
  * reporting.
  * validation.
  * CLI status.
  * result aggregation.

* Risks of partial implementation:

  * Changing path construction without manifest conversion changes can make artifacts unreadable or misclassified.

* Canonical tickets:

  * `TKT-005`
  * `TKT-006`

### RC-004 — Generic Package Boundaries May Be Contaminated by Higher-Level Semantics

* Root cause:

  * Static package observations indicate potential reverse dependencies and cross-layer coupling among artifacts, scoring, evaluation, validation, and reporting.

* Findings consolidated:

  * `FND-010`
  * `FND-011`
  * `FND-012`
  * `FND-017`

* Evidence:

  * `artifacts -> evaluation -> scoring -> artifacts` is present in the static package graph.
  * `reporting -> attacks` exists.
  * generic and CP2 score loading coexist.
  * validation responsibilities appear in several packages.

* Why these findings belong together:

  * They all concern package ownership, dependency direction, and semantic layering.

* Conceptual ownership:

  * Artifacts own transport, names, layout, lifecycle, and existence primitives.
  * Scoring owns persisted score schema and generic score loading.
  * Evaluation owns generic metric formulas.
  * Validation owns cross-artifact and protocol validation.
  * Reporting owns rendering and generic report assembly.
  * CP2-specific result interpretation remains in attacks.

* Affected conceptual areas:

  * imports.
  * public package initialization.
  * score parsing.
  * metric validation.
  * result validation.
  * report generation.
  * artifact existence.

* Configuration impact:

  * Configuration must not import higher-level domain behavior merely to resolve paths or serialize settings.

* Enum impact:

  * Low.

* Dataclass impact:

  * Stable data-transfer models may be needed between packages, but no generic mega-model should be introduced.

* Constant/raw-string impact:

  * Low.

* Validation impact:

  * High.

* CLI or public-interface impact:

  * CLI should route to package-owned orchestration rather than invoking cross-layer helpers directly.

* Artifact and manifest impact:

  * Medium.

* Serialization impact:

  * Medium.

* Result-loading and reporting impact:

  * High.

* Test impact:

  * Static import checks, package import tests, cross-package integration tests, and public re-export tests.

* Documentation impact:

  * Package responsibility documentation must be updated after verified changes.

* Reproducibility impact:

  * Medium.

* Scientific or protocol impact:

  * Medium.

* Upstream dependencies:

  * Artifact schema and CP2 manifest contracts.

* Downstream consequences:

  * Import cycles, package initialization fragility, reporting coupling, validation inconsistency.

* Risks of partial implementation:

  * Removing one import without relocating its responsibility may weaken validation or artifact safety.

* Canonical tickets:

  * `TKT-007`
  * `TKT-008`
  * `TKT-009`
  * `TKT-011`

### RC-005 — CP2 Scientific Computation Needs Narrow Explicit Boundaries Between Policy Dispatch, Generic Metrics, and CP2 Paired Metrics

* Root cause:

  * CP2 has justified policy-specific and attack-specific computations, but dispatch and metric layering may not be centralized.

* Findings consolidated:

  * `FND-013`
  * `FND-014`

* Evidence:

  * Separate B1/B2 and B4 recomputation functions exist.
  * `recompute_pair` and `_run_policy_pair` coexist.
  * Generic metric computation and CP2 metric engine coexist.
  * `lock_mu_flag_threshold` and `compute_mu_flag_threshold` coexist.

* Why these findings belong together:

  * They all concern preserving distinct scientific semantics while avoiding duplicate dispatch and mathematical formulas.

* Conceptual ownership:

  * B1/B2/B4 remain distinct implementations.
  * One public CP2 policy dispatcher should coordinate them.
  * Generic metrics remain in evaluation.
  * Paired, delta, spillover, AUROC-invariance, and CP2-specific metrics remain in attacks.

* Affected conceptual areas:

  * threshold recomputation.
  * policy selection.
  * B3 rejection.
  * B4 decomposition.
  * AUROC invariance.
  * mu-flag threshold locking.
  * CP2 metric fields.
  * report interpretation.

* Configuration impact:

  * Typed B4 and threshold config must cross one validated boundary.

* Enum impact:

  * Threshold policy must remain enum-driven.

* Dataclass impact:

  * `PolicyPair`, `B4ThresholdPair`, `MetricResult`, and generic evaluation results must remain separate.

* Constant/raw-string impact:

  * Low.

* Validation impact:

  * Policy validation and result invariants must be explicit.

* CLI or public-interface impact:

  * CLI must not dispatch policy implementations independently.

* Artifact and manifest impact:

  * CP2 metrics must be persisted without formula duplication.

* Serialization impact:

  * Policy-specific B4 fields require compatibility-aware mapping.

* Result-loading and reporting impact:

  * Report code must preserve policy-specific semantics.

* Test impact:

  * B1/B2/B4 semantic tests, B3 rejection tests, B4 decomposition tests, AUROC invariance tests, and mu-flag locking tests.

* Documentation impact:

  * Policy-specific behavior must remain documented separately.

* Reproducibility impact:

  * High.

* Scientific or protocol impact:

  * High.

* Upstream dependencies:

  * B4 configuration ownership.
  * protocol matrix ownership.

* Downstream consequences:

  * result rows.
  * manifests.
  * reporting.
  * validation.

* Risks of partial implementation:

  * A generic dispatcher that erases B4 decomposition would be protocol drift.

* Canonical tickets:

  * `TKT-003`
  * `TKT-010`

### RC-006 — Orchestration, CLI, and Validation Responsibilities Need Explicit Layer Boundaries

* Root cause:

  * CP2 bounded sweeps are represented across matrix enumeration, cell execution, aggregate runs, persistence, CLI commands, and validation modules.

* Findings consolidated:

  * `FND-015`
  * `FND-016`
  * `FND-017`

* Evidence:

  * Matrix, cell, run, manifest, CLI, and validation modules are separately enumerated.
  * Duplicate command names occur in several CLI modules.
  * validation-related functions exist in several packages.

* Why these findings belong together:

  * They concern command-facing lifecycle behavior and the path from user input to scientific execution and artifacts.

* Conceptual ownership:

  * CLI owns command parsing and user-facing output.
  * Matrix owns deterministic condition enumeration.
  * cell runner owns pure CP2 execution.
  * sweep runner owns orchestration.
  * artifact modules own writes and lifecycle.
  * validation owns cross-artifact and protocol checks.

* Affected conceptual areas:

  * CLI preview.
  * CLI dry-run.
  * smoke execution.
  * bounded sweep execution.
  * status.
  * result validation.
  * resume behavior.
  * failure diagnostics.

* Configuration impact:

  * CLI must consume resolved configuration rather than construct scientific settings independently.

* Enum impact:

  * CLI parsing must normalize to canonical enums.

* Dataclass impact:

  * CLI must pass typed request/specification models rather than loose primitive groups.

* Constant/raw-string impact:

  * CLI must not own duplicate raw command-to-policy mappings.

* Validation impact:

  * High.

* CLI or public-interface impact:

  * High.

* Artifact and manifest impact:

  * High.

* Serialization impact:

  * Medium.

* Result-loading and reporting impact:

  * Medium.

* Test impact:

  * CLI registration, help, dry-run, smoke, error-path, status, resume, and command-to-orchestrator tests.

* Documentation impact:

  * Command names and scopes require explicit documentation.

* Reproducibility impact:

  * High.

* Scientific or protocol impact:

  * High.

* Upstream dependencies:

  * canonical identity.
  * protocol config.
  * artifact lifecycle.
  * policy dispatcher.

* Downstream consequences:

  * CP2 execution reliability and safe resumption.

* Risks of partial implementation:

  * Different code paths for smoke, dry-run, and real execution can diverge from the same protocol locks.

* Canonical tickets:

  * `TKT-011`

### RC-007 — Test, Architecture, and Empty-Package Hygiene Require Controlled Cleanup Rather Than Broad Deletion

* Root cause:

  * The repository has dedicated test support and architecture tests, plus an empty package, but the inventory does not prove duplication or dead code.

* Findings consolidated:

  * `FND-018`
  * `FND-020`
  * `FND-021`

* Evidence:

  * `testsupport` contains reusable fixture factories.
  * many package-specific tests exist.
  * architecture tests exist.
  * `analyses` is explicitly empty.
  * `core` is broad but already leaf-layer and modular.

* Why these findings belong together:

  * They all concern cleanup discipline, test ownership, and avoiding unnecessary structural change.

* Conceptual ownership:

  * `testsupport` owns reusable test-only fixtures.
  * architecture tests own semantic dependency and ownership constraints.
  * `analyses` has no evidenced responsibility until verified.
  * `core` remains the low-level foundation.

* Affected conceptual areas:

  * test fixture construction.
  * import boundaries.
  * package cleanup.
  * architecture guard tests.
  * public package imports.

* Configuration impact:

  * None expected.

* Enum impact:

  * Low.

* Dataclass impact:

  * Synthetic fixture contracts may construct domain types.

* Constant/raw-string impact:

  * Architecture tests can detect stale direct constant imports.

* Validation impact:

  * Test support must preserve intended invalid-state fixtures.

* CLI or public-interface impact:

  * Low, except if `analyses` is a public namespace.

* Artifact and manifest impact:

  * Low.

* Serialization impact:

  * Low.

* Result-loading and reporting impact:

  * Low.

* Test impact:

  * High.

* Documentation impact:

  * `analyses` status must be documented if retained.

* Reproducibility impact:

  * Medium.

* Scientific or protocol impact:

  * Medium because fixture semantics can influence CP2 invariant coverage.

* Upstream dependencies:

  * All prior tickets that change architectural boundaries.

* Downstream consequences:

  * Long-term refactor safety and test maintainability.

* Risks of partial implementation:

  * Over-centralizing fixtures can erase policy-specific test cases.

* Canonical tickets:

  * `TKT-012`

---

## 6. Remediation Strategy and Execution Order

The remediation strategy is intentionally staged.

The first goal is not code movement. The first goal is to protect the existing scientific contract and establish verification gates.

The second goal is canonical semantic ownership:

1. CP2 protocol values and seed pools.
2. B4 configuration.
3. CP2 condition and run identity.

The third goal is compatibility-safe persistence cleanup:

1. lifecycle marker interpretation.
2. CP2 path identity.
3. manifest conversion.
4. JSON transport ownership.

The fourth goal is dependency and computation cleanup:

1. score schema ownership.
2. artifact/evaluation/scoring dependency direction.
3. reporting dependency direction.
4. policy dispatch and CP2 metric boundary.

The fifth goal is orchestration clarity:

1. bounded sweep lifecycle.
2. CLI routing.
3. validation-scope map.
4. status and resume behavior.

The sixth goal is cleanup only after behavior is protected:

1. test-support consolidation.
2. architecture test modernization.
3. empty `analyses` package decision.

The program must not begin with:

* moving enums based only on package aesthetics;
* renaming output roots;
* replacing all raw strings;
* merging all manifest models;
* merging generic and CP2 layouts;
* moving all constants to YAML;
* replacing policy-specific code with a generic abstraction;
* deleting empty packages without usage verification;
* changing artifact paths before compatibility tests exist.

---

## 7. Implementation Phases

### Phase 00 — Contract and Terminology Stabilization

* Phase objective:

  * Establish explicit behavioral, scientific, artifact, and compatibility locks before structural refactoring.

* Tickets in strict execution order:

  1. `TKT-001`

* Entry conditions:

  * No outstanding source modification from this backlog has started.
  * Existing CP2 tests, artifact fixtures, and package import tests are available for inspection during later implementation.

* Dependencies:

  * None.

* Risks:

  * Refactoring without captured behavior could create undetectable scientific drift.

* Phase-level acceptance criteria:

  * A CP2 refactor acceptance matrix exists.
  * Every high-risk future ticket has precise source-verification questions.
  * Existing scientific invariants are mapped to concrete tests or gaps.

* Required phase-end audits:

  * Contract-correctness audit.
  * CP2 protocol-safety audit.
  * test/artifact/documentation integrity audit.

### Phase A — Canonical Types, Enums, Configuration, and Constants

* Phase objective:

  * Establish canonical ownership for CP2 scientific values, B4 configuration, seed pools, matrix definitions, raw-domain vocabulary, and CP2 identity.

* Tickets in strict execution order:

  1. `TKT-002`
  2. `TKT-003`
  3. `TKT-004`

* Entry conditions:

  * `TKT-001` must be `AUDITED`.

* Dependencies:

  * Protocol configuration ownership must be decided before B4 and CP2 identity projections are changed.

* Risks:

  * Changing effective values, seed semantics, or B4 parameter flow can alter scientific results.
  * Incorrectly merging generic and CP2 config can create cross-protocol contamination.

* Phase-level acceptance criteria:

  * Every CP2 scientific parameter has one semantic owner.
  * B4 parameter flow is typed and validated.
  * CP2 identity has explicit condition and run semantics.
  * Existing serialized fields remain unchanged.

* Required phase-end audits:

  * Effective configuration and seed audit.
  * B4 reproducibility audit.
  * identity/path/manifest compatibility audit.

### Phase B — Artifact Integrity, Serialization, and Resume Safety

* Phase objective:

  * Clarify CP2 artifact layout, lifecycle, manifest construction, and transport without breaking existing outputs.

* Tickets in strict execution order:

  1. `TKT-005`
  2. `TKT-006`
  3. `TKT-007`

* Entry conditions:

  * `TKT-002`, `TKT-003`, and `TKT-004` must be `AUDITED`.

* Dependencies:

  * Canonical CP2 identity is required before path and manifest derivation can be consolidated.
  * Effective protocol configuration is required before manifest provenance is stabilized.

* Risks:

  * Existing artifact discovery and resume logic can fail if names, markers, paths, or schemas drift.
  * Persisted scientific evidence can become inconsistent with runtime objects.

* Phase-level acceptance criteria:

  * Lifecycle semantics are mapped explicitly.
  * Existing path strings remain compatible.
  * Result-to-manifest conversion is singular and validated.
  * CP2 score loading has one schema interpretation owner.

* Required phase-end audits:

  * Existing-artifact compatibility audit.
  * lifecycle/resume audit.
  * manifest and score-schema round-trip audit.

### Phase C — Runtime Diagnostics and Package-Boundary Hardening

* Phase objective:

  * Remove unsupported dependency direction, clarify score/evaluation boundaries, and isolate CP2-specific report preparation.

* Tickets in strict execution order:

  1. `TKT-008`
  2. `TKT-009`
  3. `TKT-010`

* Entry conditions:

  * Phase B must be `AUDITED`.

* Dependencies:

  * Artifact and manifest ownership must be stable before dependency inversion.
  * B4 configuration and protocol matrix ownership must already be stable before policy-dispatch cleanup.

* Risks:

  * A dependency inversion can weaken validation if responsibilities are moved incorrectly.
  * A generic dispatcher can unintentionally flatten B4 semantics.

* Phase-level acceptance criteria:

  * No unjustified package-level cycle remains.
  * Generic reporting does not execute or own CP2 scientific computation.
  * B1/B2/B4 remain policy-specific and test-equivalent.
  * Generic metrics and CP2 paired metrics have explicit ownership boundaries.

* Required phase-end audits:

  * Static dependency audit.
  * policy/metric semantic audit.
  * generic-versus-CP2 reporting separation audit.

### Phase D — CLI, Orchestration, Validation, and Operational Observability

* Phase objective:

  * Make CLI commands thin, make sweep execution layered, and clarify validation ownership and resume safety.

* Tickets in strict execution order:

  1. `TKT-011`

* Entry conditions:

  * Phase C must be `AUDITED`.

* Dependencies:

  * Canonical identity, configuration, lifecycle, manifests, and policy dispatch must be stable.

* Risks:

  * Divergence between dry-run, smoke, and real execution can alter the CP2 protocol.
  * CLI renames can break automation.
  * validation scope changes can silently weaken safety gates.

* Phase-level acceptance criteria:

  * CLI commands delegate rather than implement scientific behavior.
  * Bounded-sweep matrix, smoke, dry-run, and run paths share protocol locks.
  * validation scopes are explicit.
  * resume behavior distinguishes complete, partial, corrupt, and aborted outputs.

* Required phase-end audits:

  * CLI contract audit.
  * sweep/protocol propagation audit.
  * artifact/status/resume audit.

### Phase E — Test Support, Documentation, and Controlled Cleanup

* Phase objective:

  * Consolidate reusable test support, preserve semantic architecture checks, and decide the status of the empty package.

* Tickets in strict execution order:

  1. `TKT-012`

* Entry conditions:

  * Phase D must be `AUDITED`.

* Dependencies:

  * All moved or refactored ownership boundaries must already be stable.

* Risks:

  * Over-centralized fixtures can hide meaningful scientific differences.
  * Removing `analyses` may break public imports if it is a compatibility namespace.

* Phase-level acceptance criteria:

  * `testsupport` remains test-only.
  * architecture tests enforce semantic boundaries rather than incidental file structure.
  * `analyses` is either intentionally retained or safely removed.
  * stale references are eliminated or retained as explicit compatibility aliases.

* Required phase-end audits:

  * test-support boundary audit.
  * architecture test quality audit.
  * package cleanup and stale-reference audit.

### Phase F — Integration, Regression, and Final Hardening

* Phase objective:

  * Validate the entire remediation program against scientific, artifact, package, CLI, and test contracts.

* Tickets in strict execution order:

  * No new implementation ticket.
  * Execute the five final program audits in Section 11.

* Entry conditions:

  * `TKT-001` through `TKT-012` are either:

    * `AUDITED`
    * `REJECTED`
    * `SUPERSEDED`
    * or `DEFERRED` with documented justification.

* Dependencies:

  * All mandatory tickets.

* Risks:

  * Late discovery of compatibility or protocol drift.

* Phase-level acceptance criteria:

  * No unresolved P0 or P1 issue remains.
  * No unauthorized scientific scope expansion occurred.
  * Existing artifacts remain readable or have an explicit migration plan.
  * Public command and import compatibility is documented.

* Required phase-end audits:

  * All five final audits.

---

## 8. Detailed Ticket Backlog

### TKT-001 — Establish the CP2 Refactor Contract and Behavioral Lock Suite

* Status: `PLANNED`
* Priority: `P0`
* Phase:

  * Phase 00 — Contract and Terminology Stabilization
* Root cause:

  * `RC-001`
  * `RC-002`
  * `RC-003`
  * `RC-005`
* Finding references:

  * `FND-001`
  * `FND-002`
  * `FND-003`
  * `FND-004`
  * `FND-005`
  * `FND-006`
  * `FND-008`
  * `FND-013`
  * `FND-014`
  * `FND-015`
* Depends on:

  * None.
* Blocks:

  * `TKT-002`
  * `TKT-003`
  * `TKT-004`
  * `TKT-005`
  * `TKT-006`
  * `TKT-010`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.validation`
  * `datp.attacks.guardrails`
  * CP2-focused unit and integration test suites.
* Change classification:

  * `TEST_COVERAGE`
* Implementation mode:

  * `CODE_CHANGE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High test and acceptance impact; low runtime behavior impact if implemented correctly.
* Evidence confidence:

  * High.

#### 1. Problem Statement

The inventories show multiple CP2-sensitive boundaries:

* paired seed identity;
* no in-place mutation;
* B3 exclusion;
* B1/B2/B4 behavior;
* B4 decomposition;
* AUROC invariance;
* artifact path compatibility;
* manifest compatibility;
* lifecycle and resume behavior.

Future refactoring cannot safely proceed unless these contracts are converted into explicit acceptance evidence.

#### 2. Evidence and Consolidated Rationale

The inventories identify:

* guardrail functions for mutation, reservoir restrictions, B3 exclusion, fractions, and bounded target scope;
* deterministic seed derivation;
* B4 recomputation and decomposition models;
* CP2 metric and AUROC functions;
* typed manifests and layouts;
* attack-focused unit and integration test areas.

The inventories do not establish whether every critical protocol contract already has sufficient regression coverage. Therefore, the ticket creates a verified refactor lock suite rather than assuming existing coverage is complete.

#### 3. Current Intended Contract

The current intended CP2 contract includes:

* score-level calibration poisoning only;
* clean model/training/test artifacts;
* paired clean and poisoned conditions;
* B1/B2/B4 only;
* B3 exclusion;
* deterministic seed separation;
* no mutation of original calibration arrays;
* B4 client-effective threshold semantics;
* stable artifact names, paths, and manifest fields;
* unchanged test score basis for AUROC checks.

#### 4. Required Outcome

A later implementation agent must be able to demonstrate, before and after every sensitive refactor, that:

* CP2 behavior is scientifically equivalent for unchanged inputs;
* artifacts remain compatible;
* manifests remain semantically equivalent;
* seeds remain deterministic;
* B4 remains reproducible;
* clean-versus-poisoned pairing remains intact.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* change CP2 protocol values;
* add new attack families;
* modify the model;
* modify training behavior;
* modify test sets;
* rewrite B1/B2/B4 logic;
* rename artifact paths;
* alter manifest schemas;
* delete meaningful existing tests;
* use test changes to mask a behavior regression.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify future coverage for:

* `datp.core.seed_sequence`
* `datp.attacks.guardrails`
* `datp.attacks.injector`
* `datp.attacks.b4_recompute`
* `datp.attacks.metric_engine`
* `datp.attacks.bounded_sweep_matrix`
* `datp.attacks.bounded_sweep_cell`
* `datp.artifacts.poison_layout`
* `datp.attacks.bounded_sweep_manifest`
* `datp.attacks.run_manifest`
* `datp.artifacts.lifecycle`

#### 7. Detailed Future Verification Steps

1. Inventory current tests protecting:

   * seed determinism;
   * no in-place mutation;
   * reservoir restrictions;
   * B3 exclusion;
   * fraction-grid enforcement;
   * bounded single-client scope;
   * B1/B2/B4 output semantics;
   * B4 decomposition;
   * AUROC invariance;
   * artifact path generation;
   * manifest serialization;
   * lifecycle markers.

2. Identify missing direct regression tests.

3. Capture representative synthetic CP2 cases covering:

   * clean control fraction `0.0`;
   * high-score benign source;
   * low-score benign source;
   * random benign control;
   * one B1 condition;
   * one B2 condition;
   * one B4 condition;
   * one B4 churn condition;
   * one infeasible reservoir case;
   * one invalid B3 request.

4. Preserve synthetic fixture semantics:

   * eligible client;
   * pending client;
   * degenerate-tail client;
   * calibration/test separation.

5. Add artifact compatibility snapshots only after verifying that snapshots represent intended stable contracts rather than incidental JSON formatting.

#### 8. Detailed Implementation Plan

1. Create a CP2 refactor acceptance checklist in the test and validation layer.
2. Group tests by invariant rather than solely by package:

   * identity;
   * seed;
   * policy;
   * metrics;
   * artifact;
   * lifecycle;
   * manifest;
   * CLI propagation.
3. Ensure each sensitive future ticket references this contract suite.
4. Add missing tests only where the inventory establishes a meaningful scientific or compatibility contract.
5. Ensure tests assert behavior rather than internal implementation layout.
6. Preserve existing architecture tests until equivalent semantic boundary tests exist.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Use existing enums for policy, source, objective, target scope, and scale.
* Do not introduce parallel test-only enums.
* Use canonical test fixtures rather than raw-string conditions where typed constructors exist.
* Preserve raw path strings and serialized field values as compatibility expectations.
* Record B4 values explicitly in tests:

  * `K`
  * `n_init`
  * `max_iter`
  * `random_state`
* Do not hardcode scientifically significant values in unrelated test helpers.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* This ticket must precede every ticket affecting:

  * seed pools;
  * B4 parameters;
  * CP2 identity;
  * paths;
  * manifests;
  * policy dispatch;
  * metrics;
  * orchestration.
* It does not alter public interfaces directly.
* It increases future refactor safety by identifying compatibility-sensitive behavior before implementation changes.

#### 11. Test Plan

Required focused tests:

* Seed derivation determinism tests.
* Clean-versus-poisoned pairing tests.
* B3 rejection tests.
* no-in-place mutation tests.
* reservoir-not-training-or-test tests.
* B1/B2/B4 policy semantic tests.
* B4 decomposition sum tests.
* AUROC invariance tests.
* fraction-grid and target-scope guardrail tests.
* path compatibility tests.
* manifest serialization round-trip tests.
* lifecycle marker state tests.
* malformed/partial artifact rejection tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* No current artifact schema may change.
* Add tests for:

  * complete runs;
  * in-progress runs;
  * aborted runs;
  * malformed marker combinations;
  * missing manifest;
  * partial manifest;
  * incorrect seed record;
  * mismatched path/manifest identity.
* Resume behavior must reject incomplete or inconsistent artifacts.

#### 13. Documentation and Terminology Requirements

Document:

* the distinction between clean artifacts and poisoned calibration variants;
* the difference between training seed and poisoning seed;
* the meaning of B4 effective threshold;
* the meaning of artifact completeness;
* the difference between a valid clean control and an incomplete run.

#### 14. Acceptance Criteria

* Every CP2 non-negotiable is mapped to at least one executable test or an explicitly documented test gap.
* No required future ticket lacks identified protocol regression checks.
* The test suite can detect:

  * B3 reintroduction;
  * seed drift;
  * B4 parameter drift;
  * path drift;
  * manifest drift;
  * mutation regressions;
  * AUROC regressions.
* No production behavior is intentionally changed.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * Test inventory mapping.
     * New or confirmed invariant tests.
     * No unrelated production behavior changes.
     * No duplicate test abstractions introduced.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * CP2 protocol checklist maps tests across core, attacks, artifacts, config, thresholding, evaluation, and validation.
     * Tests explicitly preserve pairing, policy scope, seed semantics, and B4 semantics.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * Focused tests pass.
     * Negative tests exist for invalid protocol states.
     * Artifact and manifest fixtures remain valid.
     * Test naming and documentation distinguish protocol contracts from implementation details.

#### 16. Completion Evidence Required

* Refactor contract checklist.
* Test-to-contract mapping.
* Passing focused CP2 test suite.
* Passing artifact and manifest compatibility tests.
* Documented unresolved coverage gaps, if any.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Highest risk:

  * Tests may capture incidental current behavior instead of intended contract.
* Rollback trigger:

  * A proposed test requires changing scientific outputs without clear protocol authorization.
* Protocol-drift trigger:

  * A future ticket cannot prove unchanged pairing, B4 behavior, or artifact compatibility.

---

### TKT-002 — Establish One Typed Ownership Chain for CP2 Protocol Values, Seed Pools, Matrix Definitions, and Enum Boundaries

* Status: `PLANNED`
* Priority: `P0`
* Phase:

  * Phase A — Canonical Types, Enums, Configuration, and Constants
* Root cause:

  * `RC-002`
* Finding references:

  * `FND-002`
  * `FND-004`
  * `FND-005`
  * `FND-019`
* Depends on:

  * `TKT-001`
* Blocks:

  * `TKT-003`
  * `TKT-004`
  * `TKT-005`
  * `TKT-006`
  * `TKT-010`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.config.attack_config`
  * `datp.core.poison_enums`
  * `datp.artifacts.poison_names`
  * `datp.config.models`
* Change classification:

  * `CONFIGURATION_CONTRACT`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High.
* Evidence confidence:

  * High for duplicated ownership risk; medium for exact target implementation.

#### 1. Problem Statement

CP2 values and allowed condition sets appear across:

* code-owned constants;
* generic configuration models;
* CP2 configuration models;
* YAML defaults;
* enum tuple collections;
* function defaults;
* guardrails;
* path and manifest boundary values.

Without an explicit ownership chain, a future change can alter runtime behavior, manifest representation, and documentation inconsistently.

#### 2. Evidence and Consolidated Rationale

The inventories establish:

* CP2 seed pools in `datp.artifacts.poison_names`.
* Seed-related configuration in `SeedPools` and generic `experiment.seeds`.
* Bounded and full sweep grids in `datp.core.poison_enums`.
* B4 values, threshold quantile, eligibility values, and trim values in code constants.
* overlapping YAML values.
* raw domain strings matching existing enums.
* matrix builders and guardrails that consume related values.

The inventories do not establish whether every duplicate is a real conflict. Therefore this ticket must classify each repeated representation before any code change.

#### 3. Current Intended Contract

The intended ownership boundary is:

* Closed domain vocabulary:

  * enums.
* CP2 protocol locks:

  * typed CP2 configuration and code-owned immutable defaults.
* Generic DATP behavior:

  * generic configuration models.
* Artifact compatibility values:

  * artifact names, output roots, path fragments, serialized string values.
* Derived run values:

  * effective configuration, resolved matrix, seed derivation records.
* Boundary strings:

  * CLI, YAML, manifests, paths, and score schema.

#### 4. Required Outcome

A future implementation must establish:

* one explicit semantic owner for every CP2 scientific value;
* one typed effective CP2 configuration object;
* one protocol matrix owner for policies, objectives, sources, fractions, and scopes;
* no unverified duplicate source of truth;
* stable external strings, YAML keys, paths, and manifest fields.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* move every constant into YAML;
* treat every YAML setting as editable for CP2;
* merge unrelated equal numeric values;
* alter `B1_GLOBAL`, `B2_PERSONALIZED`, or `B4_CLUSTER` serialization values;
* introduce B3 into the default matrix;
* broaden diagnostic-only values into main execution;
* rename artifact output roots;
* replace compatibility strings with enum member names unless explicitly serialized already;
* create another global constants module.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* `datp.artifacts.poison_names`
* `datp.core.poison_enums`
* `datp.config.attack_config`
* `datp.config.models`
* YAML config composition
* guardrails
* matrix enumeration
* CLI configuration resolution
* manifest configuration serialization
* direct constant imports
* direct raw-string comparisons

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Which repeated values have the same semantic meaning and which are merely equal literals?

* Evidence required:

  * Source-level call paths from:

    * constants;
    * config models;
    * YAML composition;
    * CLI;
    * matrix enumeration;
    * guardrails;
    * manifests;
    * policy recomputation.

* Conditions that authorize a code change:

  * A repeated value is proven to represent the same concept in more than one active ownership location.
  * A typed configuration or canonical protocol model can replace the duplicate without changing effective values.
  * Existing serialized and artifact representations remain compatible.

* Conditions that close the ticket with no code change:

  * Two same-valued settings are confirmed to have distinct semantics.
  * Existing separation is intentional and documented.

* Forbidden premature changes:

  * Removing constants.
  * changing YAML defaults.
  * altering matrix cardinality.
  * changing policy tuples.
  * changing enum serialization values.
  * changing seed tuples.

* Dependent tickets that must wait:

  * `TKT-003`
  * `TKT-004`
  * `TKT-010`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Create a semantic ownership register for every repeated CP2 value.

2. Classify each occurrence as one of:

   * immutable protocol lock;
   * generic DATP configuration;
   * CP2 typed configuration;
   * compatibility constant;
   * derived runtime value;
   * local formatting literal;
   * unrelated coincidental equal literal.

3. Use `SeedPools` as the candidate typed CP2 owner for:

   * training seeds;
   * poisoning seeds;
   * analysis seeds;
   * compromise-pattern seed.

4. Preserve `SeedRecord` as the canonical runtime derivation record and `SeedRecordModel` as a serialized boundary projection.

5. Establish one CP2 protocol-matrix representation for:

   * policies;
   * sources;
   * objectives;
   * fractions;
   * target scopes;
   * scale-specific conditions.

6. Make matrix enumeration and guardrails consume that same validated representation only after source verification confirms duplicated matrix ownership.

7. Keep:

   * output roots;
   * artifact names;
   * manifest file names;
   * run file names;
   * path fragments;
     inside artifact ownership.

8. Replace raw internal comparisons with enums only when source inspection confirms they are not compatibility boundaries.

9. Preserve raw strings at:

   * CLI input boundaries;
   * YAML boundaries;
   * manifest serialization boundaries;
   * path construction boundaries;
   * persisted score schema boundaries.

10. Add an effective-configuration serialization path that records actual CP2 values used for a run without redefining output schemas prematurely.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Canonical enums remain the owner for:

  * policies;
  * objectives;
  * sources;
  * injection rules;
  * target scopes;
  * defenses;
  * experiment scale;
  * datasets;
  * regimes;
  * baselines.

* `SeedPools` remains distinct from:

  * `SeedRecord`;
  * `SeedRecordModel`;
  * generic `ExperimentConfig`.

* Preserve separate semantic treatment for:

  * `TAIL_MASS`;
  * fraction grids;
  * trim fractions;
  * dataset split fractions;
  * threshold quantile;
  * confidence interval level;
  * B4 random state;
  * bootstrap seed.

* Every code-owned scientific lock must declare:

  * owner;
  * default;
  * allowed values;
  * runtime validation boundary;
  * manifest representation;
  * compatibility behavior.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Must precede:

  * B4 runtime parameter consolidation.
  * canonical CP2 identity.
  * matrix/guardrail cleanup.
  * CLI orchestration cleanup.

* Affects:

  * configuration composition;
  * manifests;
  * CLI parsing;
  * matrix enumeration;
  * guardrails;
  * policy dispatch;
  * tests;
  * documentation.

* Compatibility risk:

  * High if YAML defaults, enum values, or manifest fields change.
  * Low if internal values are derived while external representation remains stable.

#### 11. Test Plan

* Effective configuration tests.
* Seed-pool membership tests.
* mismatch rejection tests.
* matrix cardinality tests.
* bounded-matrix exact-set tests.
* full-matrix exact-set tests.
* B3 exclusion tests.
* diagnostic-only source exclusion tests.
* enum serialization tests.
* CLI parsing tests.
* YAML parsing tests.
* manifest resolved-value tests.
* direct stale-constant-import scans.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing manifest key names remain stable.
* Effective configuration must be recorded through approved manifest fields or additive compatibility-safe fields only.
* Resume logic must reject artifacts whose effective configuration does not match expected protocol lock values.
* Artifact path behavior must not depend on a new mutable protocol configuration unless explicitly authorized.

#### 13. Documentation and Terminology Requirements

Document:

* protocol lock versus editable generic configuration;
* seed pool versus seed derivation record;
* bounded versus full matrix;
* main gray-box source versus diagnostic-only source;
* enum value versus serialized boundary string;
* compatibility constant versus scientific parameter.

#### 14. Acceptance Criteria

* Every CP2 scientific value has one documented semantic owner.
* No active CP2 path reads an unclassified duplicate scientific default.
* Matrix builders and guardrails are shown to consume the same allowed-condition definition or are explicitly documented as intentionally distinct.
* B3 remains excluded from the default CP2 matrix.
* Existing strings, manifests, paths, and CLI inputs remain compatible.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * Ownership register.
     * Source-to-owner mapping.
     * No duplicate scientific source of truth remains unless documented as intentional separation.
     * Existing public values remain unchanged.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * Config propagates through CLI, matrix enumeration, guardrails, execution, manifests, and reporting.
     * B3 exclusion remains enforced.
     * Seed pools preserve paired-run behavior.
     * No new CP2 scope is introduced.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * Effective-config tests pass.
     * Matrix tests pass.
     * enum serialization tests pass.
     * artifact and manifest outputs remain compatible.
     * terminology documentation distinguishes locks from editable config.

#### 16. Completion Evidence Required

* Protocol ownership register.
* Verified effective configuration path.
* Matrix equivalence evidence.
* Passing seed, config, enum, and guardrail tests.
* Stale-reference report for deprecated constant access paths.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * matrix cardinality changes;
  * policy/source/objective combinations change;
  * seed values change;
  * manifests record different effective values;
  * B3 becomes accepted;
  * existing CLI or YAML forms break.
* Defer if:

  * generic and CP2 values have intentionally distinct meanings.

---

### TKT-003 — Consolidate CP2 B4 Parameter Flow Through a Typed B4 Configuration Boundary

* Status: `PLANNED`
* Priority: `P0`
* Phase:

  * Phase A — Canonical Types, Enums, Configuration, and Constants
* Root cause:

  * `RC-002`
  * `RC-005`
* Finding references:

  * `FND-003`
  * `FND-004`
  * `FND-013`
* Depends on:

  * `TKT-001`
  * `TKT-002`
* Blocks:

  * `TKT-010`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.config.attack_config.B4ClusterConfig`
  * `datp.config.models.ThresholdConfig`
  * `datp.attacks.b4_recompute`
* Change classification:

  * `CONFIGURATION_CONTRACT`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High for B4 behavior; medium for public interfaces.
* Evidence confidence:

  * High.

#### 1. Problem Statement

B4 parameters currently appear as:

* CP2 constants;
* generic threshold config fields;
* CP2 `B4ClusterConfig`;
* scalar parameters passed to `compute_b4_pair`.

That creates a high-risk opportunity for parameter drift and inconsistent manifest provenance.

#### 2. Evidence and Consolidated Rationale

The inventories explicitly identify:

* `B4_K`
* `B4_N_INIT`
* `B4_MAX_ITER`
* `B4_RANDOM_STATE`
* `B4ClusterConfig`
* `ThresholdConfig`
* scalar B4 function parameters.

The inventories do not establish whether generic threshold B4 settings and CP2 attack B4 settings intentionally represent different regimes. Therefore, generic and CP2 B4 configuration must not be merged until source verification confirms semantic scope.

#### 3. Current Intended Contract

For CP2 Regime A, B4 must preserve:

* `K = 3`
* `n_init = 10`
* `max_iter = 300`
* `random_state = 42`
* current fingerprint construction;
* current scaler behavior;
* current effective-threshold semantics;
* current B4 decomposition;
* current manifest representation.

#### 4. Required Outcome

A single typed CP2 B4 configuration object must carry all B4 runtime values into CP2 recomputation.

The B4 runtime path must be able to prove that:

* the values passed into recomputation;
* the values recorded in manifests;
* the values expected by protocol tests;
* and the values used in B4 decomposition

are semantically aligned.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* change `K`;
* introduce dynamic B4 selection into CP2 Regime A;
* alter B4 fingerprint content;
* change scaler behavior;
* change decomposition formula;
* alter raw cluster-label handling;
* merge B4 with B1/B2 implementations;
* remove generic `ThresholdConfig` fields without confirming their generic role;
* permit silent runtime overrides.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* `B4ClusterConfig`
* `ThresholdConfig`
* `compute_b4_pair`
* B4 call sites
* B4 manifest fields
* B4 result models
* B4 decomposition tests
* B4 CLI/config composition
* B4 reporting consumers

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Is `B4ClusterConfig` already the actual CP2 runtime source of B4 values?

* Evidence required:

  * All `compute_b4_pair` callers.
  * All direct B4 constant imports.
  * All manifest serialization paths.
  * Generic thresholding B4 configuration usage.
  * CP2 configuration composition.

* Conditions that authorize a code change:

  * Source confirms scalar B4 values are propagated independently.
  * A typed `B4ClusterConfig` can preserve all current values and call semantics.
  * Generic `ThresholdConfig` scope can be kept separate or explicitly mapped.

* Conditions that close the ticket with no code change:

  * B4ClusterConfig is already canonical and all scalar inputs derive from it through one verified path.

* Forbidden premature changes:

  * Removing B4 constants.
  * changing B4 defaults.
  * changing B4 manifest fields.
  * collapsing generic and CP2 B4 config without scope proof.

* Dependent tickets that must wait:

  * `TKT-010`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Establish whether generic `ThresholdConfig` and CP2 `B4ClusterConfig` have:

   * identical semantics;
   * overlapping semantics;
   * or distinct responsibilities.

2. Retain separate models if:

   * generic DATP B4 behavior differs from CP2 fixed-protocol B4 behavior.

3. Make `B4ClusterConfig` the sole typed CP2 runtime B4 parameter carrier.

4. Refactor CP2 recomputation interfaces to accept the typed B4 configuration object rather than independent scalar B4 arguments, while preserving compatibility wrappers if required.

5. Ensure B4 effective config is written into CP2 manifests through schema-owned provenance fields.

6. Add source-level validation that prevents:

   * missing B4 fields;
   * inconsistent B4 scalar overrides;
   * unexpected default substitution.

7. Preserve legacy constants as compatibility aliases only if source inspection proves external imports require them.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* `B4ClusterConfig` must specify:

  * allowed values;
  * default values;
  * serialization behavior;
  * compatibility behavior;
  * validation boundary.

* `ThresholdConfig` must remain generic unless verified otherwise.

* B4 constants must be classified as:

  * CP2 protocol locks;
  * compatibility aliases;
  * or obsolete duplicates.

* B4 configuration must not be represented by raw dictionaries at runtime.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Depends on protocol ownership classification.
* Affects:

  * `compute_b4_pair`;
  * policy dispatch;
  * manifests;
  * B4 decomposition;
  * tests;
  * reporting.
* Must precede policy dispatcher consolidation.
* Cannot run in parallel with `TKT-010`.

#### 11. Test Plan

* B4 deterministic-clustering tests.
* B4 clean threshold equivalence tests.
* B4 poisoned threshold equivalence tests.
* B4 decomposition equality tests.
* B4 configuration serialization tests.
* B4 manifest equivalence tests.
* invalid B4 config rejection tests.
* generic threshold B4 regression tests, if generic config is impacted.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing B4 manifest values remain present and unchanged.
* Resume logic must reject B4 artifacts where effective B4 configuration differs from the expected contract.
* No historical B4 artifact must become unreadable.

#### 13. Documentation and Terminology Requirements

Document:

* generic B4 configuration versus CP2 B4 protocol configuration;
* B4 parameters as protocol-sensitive values;
* effective threshold versus raw cluster labels;
* decomposition semantics;
* frozen procedure versus fixed client-to-cluster map.

#### 14. Acceptance Criteria

* CP2 B4 recomputation receives one typed parameter object or a verified equivalent canonical path.
* No independent CP2 scalar B4 source remains.
* B4 outputs are scientifically equivalent under unchanged inputs.
* Existing B4 manifest fields remain compatible.
* Generic B4 configuration remains untouched unless source evidence proves a necessary shared mapping.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * B4 call graph.
     * typed config mapping.
     * no unauthorized parameter change.
     * no duplicate CP2 B4 scalar source.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * CP2 config reaches recomputation, manifests, validation, reporting, and CLI consistently.
     * B4 K, seed, scaler, and decomposition semantics remain unchanged.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * B4 semantic and decomposition tests pass.
     * manifest and artifact compatibility tests pass.
     * documentation distinguishes generic and CP2 B4 scope.

#### 16. Completion Evidence Required

* B4 ownership diagram.
* B4 effective config trace.
* Passing B4 regression suite.
* Manifest compatibility evidence.
* Explicit generic/CP2 B4 scope decision.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * B4 cluster assignments, effective thresholds, or decomposition outputs change unexpectedly.
  * B4 manifests omit prior fields.
  * generic threshold behavior changes without approval.
* Defer if:

  * source verification proves different B4 config objects intentionally serve different protocols.

---

### TKT-004 — Introduce Canonical CP2 Condition and Run Identity with Explicit Boundary Projections

* Status: `PLANNED`
* Priority: `P0`
* Phase:

  * Phase A — Canonical Types, Enums, Configuration, and Constants
* Root cause:

  * `RC-001`
* Finding references:

  * `FND-001`
  * `FND-006`
  * `FND-008`
  * `FND-015`
  * `FND-022`
* Depends on:

  * `TKT-001`
  * `TKT-002`
* Blocks:

  * `TKT-005`
  * `TKT-006`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * Candidate new narrowly scoped module:

    * `datp.core.poison_identity`
* Change classification:

  * `ENUM_AND_TYPE_CONSOLIDATION`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High.
* Evidence confidence:

  * High for overlap; medium for exact target shape.

#### 1. Problem Statement

CP2 identity is manually repeated across:

* matrix specification;
* path layout;
* runtime result;
* aggregate manifest rows;
* function parameter lists;
* seed records.

The repository needs a canonical semantic representation without forcing all boundary models into one universal object.

#### 2. Evidence and Consolidated Rationale

The inventories identify overlap among:

* `SweepCellSpec`;
* `CellId`;
* `SweepCellResult`;
* `BoundedSweepResultRow`;
* `SeedRecord`;
* `run_sweep_cell`;
* `inject_single_victim`.

The field sets differ.

This indicates legitimate boundary projections with missing canonical semantic ownership.

#### 3. Current Intended Contract

The identity system must preserve distinct concepts:

* `TrainingCellId`:

  * generic training identity.
* `BaselineRunId`:

  * generic baseline identity.
* CP2 condition:

  * dataset;
  * scale;
  * policy;
  * objective;
  * source;
  * fraction;
  * target scope.
* CP2 run:

  * condition;
  * training seed;
  * poisoning seed;
  * victim or victim plan.
* seed derivation:

  * training seed;
  * poisoning seed;
  * client index;
  * scope index.
* path identity:

  * compatibility projection.
* manifest row:

  * flat compatibility projection.

#### 4. Required Outcome

A future implementation must create a narrow canonical CP2 identity layer that:

* prevents manual repetition of CP2 condition fields;
* preserves existing boundary models;
* provides explicit conversions;
* preserves existing flat serialized output;
* supports path and manifest consistency validation;
* does not merge generic training identity with CP2 attack identity.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* merge `TrainingCellId` and CP2 attack identity;
* merge `BaselineRunId` and CP2 attack identity;
* replace all boundary models with one giant model;
* add victim identity to path layout until source verification establishes need;
* change existing manifest field names;
* change path segment order;
* modify seed derivation semantics;
* add unsupported multi-client behavior.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* `SweepCellSpec`
* `CellId`
* `CellPaths`
* `SweepCellResult`
* `BoundedSweepResultRow`
* `RunManifest`
* `ProvenanceRecord`
* `SeedRecord`
* `SeedRecordModel`
* `run_sweep_cell`
* `inject_single_victim`
* `PoisonLayout.run_dir`
* path parsing and reporting consumers

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * What is the minimum CP2 identity representation that preserves current path, manifest, execution, and result semantics?

* Evidence required:

  * Constructor call sites for `SweepCellSpec`, `CellId`, `SweepCellResult`, and `BoundedSweepResultRow`.
  * Current `PoisonLayout.run_dir` composition.
  * Manifest reader behavior.
  * victim plan representation.
  * multi-client and diagnostic path behavior, if any.

* Conditions that authorize a code change:

  * A condition identity and run identity can be introduced without changing stored schema or path strings.
  * Explicit conversions can replace duplicate manual field assembly.
  * victim identity semantics are fully understood.

* Conditions that close the ticket with no code change:

  * Existing models are already constructed through a verified common source and no duplicate manual assembly exists.

* Forbidden premature changes:

  * deleting existing models;
  * changing path fields;
  * changing manifest fields;
  * adding `victim_id` into `CellId`;
  * changing equality/hash behavior without compatibility tests.

* Dependent tickets that must wait:

  * `TKT-005`
  * `TKT-006`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Define a CP2 condition identity containing only:

   * scale;
   * dataset;
   * policy;
   * objective;
   * source;
   * fraction;
   * target scope.

2. Define a CP2 run identity containing:

   * condition identity;
   * training seed;
   * poisoning seed;
   * victim identity or explicit victim-plan identity.

3. Keep `SeedRecord` separate because it represents deterministic derivation coordinates rather than run identity.

4. Keep `TrainingCellId` and `BaselineRunId` separate because they identify inherited clean-training artifacts.

5. Provide explicit conversion paths:

   * condition/run identity to `SweepCellSpec`;
   * condition/run identity to `CellId`;
   * runtime result to `BoundedSweepResultRow`;
   * seed record to `SeedRecordModel`.

6. Preserve current flat fields in manifests and result rows.

7. Add consistency validators:

   * spec equals run identity;
   * cell path equals run identity projection;
   * result equals execution identity;
   * row equals result identity;
   * provenance references the same clean source identity.

8. Replace long identity parameter lists with typed spec or run-identity arguments only where source verification proves all required fields travel together.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Use existing canonical enum types.
* Identity objects must not store unvalidated raw string values.
* Fraction must preserve validation rules.
* Seed fields remain integer typed.
* Serialization methods must preserve exact existing values.
* Path projection must preserve existing formatting.
* No generic `Identity` or `RunContext` mega-type may be introduced.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Affects:

  * paths;
  * manifests;
  * seed provenance;
  * sweep enumeration;
  * result grouping;
  * reporting;
  * CLI requests;
  * resume safety.

* Must precede:

  * CP2 path consolidation.
  * manifest conversion cleanup.
  * orchestration cleanup.

* Cannot run in parallel with:

  * `TKT-005`
  * `TKT-006`
  * `TKT-011`

#### 11. Test Plan

* Identity equality tests.
* conversion tests.
* path uniqueness tests.
* manifest row uniqueness tests.
* pair-grouping tests.
* victim-plan identity tests.
* seed derivation separation tests.
* path-to-manifest consistency tests.
* runtime-result-to-row consistency tests.
* historical manifest compatibility tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing path strings remain unchanged.
* Existing manifest rows remain flat.
* Existing path readers remain valid.
* Resume logic must distinguish:

  * same condition/new run;
  * same run/complete;
  * same run/partial;
  * conflicting identity.
* No new identity field may silently alter artifact directory placement.

#### 13. Documentation and Terminology Requirements

Document:

* training cell identity;
* baseline run identity;
* CP2 condition identity;
* CP2 run identity;
* victim plan;
* seed derivation record;
* path projection;
* manifest projection.

#### 14. Acceptance Criteria

* CP2 semantic identity has one explicit canonical owner.
* Existing boundary models remain separate and justified.
* No duplicated manual construction remains where a conversion is applicable.
* Existing path and manifest output remain compatible.
* Pairing identity is explicit and test-verified.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * identity model definitions.
     * conversion map.
     * no generic mega-model.
     * all existing distinct lifecycle models retained where justified.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * identity propagates consistently through config, matrix, execution, paths, manifests, validation, and reporting.
     * paired runs preserve seed and victim-plan identity.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * conversion, path, manifest, and pairing tests pass.
     * artifact fixtures remain discoverable.
     * documentation distinguishes semantic identity from boundary projection.

#### 16. Completion Evidence Required

* CP2 identity diagram.
* field-to-owner mapping.
* conversion test results.
* path and manifest compatibility evidence.
* explicit decision on victim identity in artifact paths.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * path uniqueness changes;
  * manifests regroup results differently;
  * paired comparisons lose seed or victim-plan alignment;
  * existing artifacts become undiscoverable.
* Defer if:

  * victim identity/path semantics cannot be established safely.

---

### TKT-005 — Formalize CP2 Artifact Layout and Lifecycle Ownership While Preserving Existing Paths and Markers

* Status: `PLANNED`
* Priority: `P1`
* Phase:

  * Phase B — Artifact Integrity, Serialization, and Resume Safety
* Root cause:

  * `RC-003`
* Finding references:

  * `FND-006`
  * `FND-007`
* Depends on:

  * `TKT-001`
  * `TKT-004`
* Blocks:

  * `TKT-006`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.artifacts.layout`
  * `datp.artifacts.poison_layout`
  * `datp.artifacts.lifecycle`
  * `datp.artifacts.names`
  * `datp.artifacts.poison_names`
* Change classification:

  * `ARTIFACT_INTEGRITY`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High artifact compatibility risk.
* Evidence confidence:

  * High.

#### 1. Problem Statement

Generic and CP2 layouts are intentionally separate, but:

* CP2 path construction uses multiple local segment builders;
* CP2 path identity overlaps with execution identity;
* generic and CP2 lifecycle vocabularies overlap;
* `CellPaths` carries marker paths that may not derive from one lifecycle owner.

#### 2. Evidence and Consolidated Rationale

The inventories identify:

* generic `ArtifactLayout`;
* CP2 `PoisonLayout`;
* generic `ArtifactFile`;
* CP2 `RunFile`;
* generic `RunState`;
* `RunLifecycle`;
* `check_run_state`;
* path formatting helpers;
* marker path fields in `CellPaths`.

The inventories do not prove equal marker literals or common lifecycle behavior.

#### 3. Current Intended Contract

The intended design keeps:

* `ArtifactLayout` for generic training, score, baseline, and checkpoint artifacts.
* `PoisonLayout` for CP2 poisoning artifacts.
* generic lifecycle semantics distinct from CP2 payload file vocabulary.
* current path segment strings stable.
* current output-root name stable.
* existing artifacts readable.

#### 4. Required Outcome

A future implementation must establish:

* one lifecycle interpretation owner;
* explicit mapping from lifecycle state to expected markers;
* CP2 path generation derived from canonical identity;
* stable existing path strings;
* documented separation between generic artifact vocabulary and CP2 payload vocabulary.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* merge `ArtifactLayout` and `PoisonLayout`;
* rename `CALIBRATION_POISONING_OUTPUT_ROOT`;
* change `f_{fraction:.2f}`;
* change scope, train-seed, or poison-seed segment formats;
* change marker names;
* move CP2 payload names into generic artifact enums;
* add a universal layout abstraction;
* add unverified victim-id path segments.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* literal values of generic and CP2 marker enums;
* `RunLifecycle` ownership;
* `check_run_state` logic;
* `PoisonLayout.run_dir`;
* `PoisonLayout.cell_paths`;
* existing artifact discovery;
* CLI status behavior;
* validation and reporting path consumers;
* historical path fixtures.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Which lifecycle markers and path segments are compatibility contracts, and which are internal implementation details?

* Evidence required:

  * Marker readers and writers.
  * lifecycle transition code.
  * status commands.
  * resume checks.
  * historical artifact fixtures.
  * path parsing or string matching behavior.

* Conditions that authorize a code change:

  * Lifecycle semantics can be centralized without changing literal marker names.
  * CP2 `CellPaths` can derive marker paths from canonical lifecycle mapping.
  * canonical identity can derive paths byte-for-byte compatibly.

* Conditions that close the ticket with no code change:

  * Generic and CP2 marker systems are intentionally different and already isolated.
  * CP2 path helpers already derive from one verified source.

* Forbidden premature changes:

  * changing marker file names;
  * changing directory structure;
  * adding path components;
  * removing aliases;
  * altering output root;
  * modifying historical artifacts.

* Dependent tickets that must wait:

  * `TKT-006`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Document artifact families:

   * generic training artifact family;
   * generic score artifact family;
   * generic baseline artifact family;
   * CP2 run payload family;
   * CP2 aggregate manifest family.

2. Map lifecycle states:

   * no state;
   * in progress;
   * complete;
   * aborted;
   * corrupt/inconsistent.

3. If marker values are semantically shared:

   * centralize state-to-marker mapping in lifecycle ownership.
   * retain enum aliases where compatibility requires.

4. Keep CP2 payload-file names in `poison_names`.

5. Make `CellPaths` derive lifecycle marker paths from lifecycle mapping rather than duplicate literals.

6. Make `PoisonLayout` derive path segments from canonical CP2 identity projections.

7. Preserve current string output exactly.

8. Add an explicit artifact identity validator:

   * identity -> path;
   * identity -> manifest;
   * path -> lifecycle state;
   * lifecycle state -> allowed marker set.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Do not merge `ArtifactFile`, `ManifestFile`, and `RunFile`.
* Separate:

  * generic file vocabulary;
  * CP2 aggregate manifest vocabulary;
  * CP2 run payload vocabulary;
  * lifecycle state interpretation.
* Path segment formatting remains owned by `poison_layout`, not a generic helper module.
* All path values remain derived from typed identity, not raw command-line strings.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Affects:

  * status;
  * resume;
  * manifest writing;
  * validation;
  * reporting;
  * CLI;
  * artifact discovery.
* Must precede manifest writer consolidation and orchestration cleanup.
* High compatibility risk if incomplete.

#### 11. Test Plan

* Generic layout tests.
* CP2 path snapshot tests.
* path uniqueness tests.
* fraction formatting tests.
* target-scope formatting tests.
* training-seed and poisoning-seed formatting tests.
* marker state matrix tests.
* corrupt marker combination tests.
* artifact discovery tests.
* historical output compatibility tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing artifact paths must remain discoverable.
* Complete artifacts must not be mistaken for partial ones.
* Partial artifacts must not be mistaken for complete ones.
* Conflicting markers must result in corrupt state.
* Resume logic must use lifecycle mapping rather than ad hoc marker checks where source verification permits.

#### 13. Documentation and Terminology Requirements

Document:

* artifact family boundaries;
* lifecycle state semantics;
* marker compatibility behavior;
* path segment meaning;
* CP2 output-root stability;
* relationship between `CellId`, `CellPaths`, and `PoisonLayout`.

#### 14. Acceptance Criteria

* Generic and CP2 layouts remain separate.
* Lifecycle ownership is explicit.
* Marker and path strings remain compatible.
* CP2 path generation is traceable to canonical identity.
* Artifact state validation rejects partial or inconsistent outputs.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * lifecycle mapping.
     * path derivation map.
     * unchanged artifact names.
     * no universal layout or duplicated marker owner introduced.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * status, resume, validation, reporting, and CLI consume the same lifecycle interpretation.
     * CP2 identity maps consistently to paths and manifests.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * lifecycle, path, discovery, and corruption tests pass.
     * historical fixtures remain readable.
     * documentation precisely states compatibility rules.

#### 16. Completion Evidence Required

* Lifecycle vocabulary map.
* Artifact family map.
* Path compatibility snapshots.
* Resume and corruption test results.
* documented marker compatibility decision.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * old artifacts are not discovered;
  * resume behavior changes;
  * paths change;
  * manifest location changes;
  * complete markers are interpreted differently.
* Defer if:

  * source inspection shows incompatible generic and CP2 marker semantics.

---

### TKT-006 — Establish Explicit CP2 Manifest Conversion and JSON Transport Boundaries

* Status: `PLANNED`
* Priority: `P1`
* Phase:

  * Phase B — Artifact Integrity, Serialization, and Resume Safety
* Root cause:

  * `RC-003`
* Finding references:

  * `FND-008`
  * `FND-009`
* Depends on:

  * `TKT-001`
  * `TKT-004`
  * `TKT-005`
* Blocks:

  * `TKT-009`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.attacks.bounded_sweep_manifest`
  * `datp.attacks.run_manifest`
  * `datp.attacks.run_logger`
  * `datp.attacks.bounded_sweep_run`
  * `datp.artifacts.io`
* Change classification:

  * `SERIALIZATION_AND_PROVENANCE`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High artifact and provenance impact.
* Evidence confidence:

  * High.

#### 1. Problem Statement

CP2 has distinct runtime and persisted models, but conversion ownership is not fully established.

Potential duplicate concerns include:

* result row assembly;
* seed-record serialization;
* provenance construction;
* manifest writing;
* JSON transport and atomic-write behavior.

#### 2. Evidence and Consolidated Rationale

The inventories identify:

* runtime result models;
* persisted manifest models;
* `_row_for_cell`;
* `build_manifest`;
* `emit_manifest`;
* `load_manifest`;
* `write_run_log_entry`;
* `write_nbaiot_bounded_sweep_manifest`;
* generic `write_json_atomic`.

This supports explicit conversion boundaries but does not prove that all writing behavior is duplicated.

#### 3. Current Intended Contract

The intended CP2 persistence model is:

* runtime calculations remain typed in CP2 scientific modules;
* per-run manifests remain distinct from aggregate bounded-sweep manifests;
* seed records and provenance are persisted through validated projections;
* generic I/O owns transport behavior;
* CP2 owns manifest schemas and scientific field interpretation.

#### 4. Required Outcome

A future implementation must make explicit:

* runtime result -> result row conversion;
* run identity + provenance -> per-run manifest conversion;
* seed record -> manifest seed model conversion;
* schema validation before persistence;
* schema validation after loading;
* generic atomic JSON transport ownership.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* merge per-run and aggregate manifests;
* flatten all CP2 models into one schema;
* change existing manifest fields;
* remove B4-specific fields;
* recompute metrics during serialization;
* move CP2 scientific schema logic into generic artifact I/O;
* introduce schema versions unless source verification establishes a compatibility need.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* `_row_for_cell`;
* `BoundedSweepResultRow`;
* `BoundedSweepManifest`;
* `RunManifest`;
* `ProvenanceRecord`;
* `SeedRecordModel`;
* `build_manifest`;
* `emit_manifest`;
* `load_manifest`;
* `write_nbaiot_bounded_sweep_manifest`;
* generic JSON writer;
* consumers in reporting and validation.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Is there one canonical conversion path for each CP2 persisted representation?

* Evidence required:

  * Every constructor call for:

    * `BoundedSweepResultRow`;
    * `BoundedSweepManifest`;
    * `RunManifest`;
    * `SeedRecordModel`;
    * `ProvenanceRecord`.
  * Every JSON write path.
  * Every JSON read path.
  * hash and provenance behavior.
  * manifest consumer behavior.

* Conditions that authorize a code change:

  * Multiple manual assembly paths exist.
  * Generic transport behavior can be centralized without changing schema semantics.
  * a conversion function can preserve all current fields.

* Conditions that close the ticket with no code change:

  * Each persisted schema already has one verified constructor and one verified transport path.

* Forbidden premature changes:

  * removing fields;
  * reordering externally significant CSV columns;
  * changing JSON keys;
  * changing null/omitted B4 semantics;
  * changing manifest location;
  * hashing different byte representations.

* Dependent tickets that must wait:

  * `TKT-009`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Retain separate models for:

   * runtime results;
   * per-run manifests;
   * bounded-sweep aggregate manifests;
   * generic metric provenance;
   * CP2 provenance.

2. Establish named conversion functions:

   * `SeedRecord -> SeedRecordModel`;
   * runtime result -> bounded row;
   * CP2 identity + seed record + provenance -> run manifest;
   * bounded row sequence -> bounded manifest.

3. Make one named conversion function the canonical result-row assembler.

4. Make CP2 schema modules own:

   * Pydantic validation;
   * field defaults;
   * explicit optional B4 semantics;
   * read-time validation.

5. Make generic artifact I/O own:

   * directory creation;
   * atomic write mechanics;
   * transport-level JSON serialization;
   * transport-level CSV serialization.

6. Preserve CP2 schema construction in CP2 modules.

7. Add post-write validation only where it does not alter write semantics.

8. Preserve historical manifest reading through compatibility-aware parsing if source inspection confirms old forms exist.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Keep:

  * runtime dataclasses;
  * Pydantic manifest models;
  * generic provenance;
  * CP2 provenance;
  * B4-specific types;
    separate.

* Do not serialize raw enum names if existing value serialization differs.

* Do not introduce untyped dict assembly when a model exists.

* Ensure all effective protocol configuration values are represented through schema-owned fields or approved provenance fields.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Depends on canonical CP2 identity and artifact lifecycle.
* Affects:

  * reports;
  * validation;
  * CLI status;
  * resume;
  * inference;
  * result loading;
  * provenance.
* Cannot run in parallel with:

  * `TKT-005`
  * `TKT-011`

#### 11. Test Plan

* Runtime-result-to-row tests.
* row-to-manifest tests.
* manifest JSON round-trip tests.
* corrupt manifest rejection tests.
* missing required field tests.
* invalid enum serialization tests.
* B4 row completeness tests.
* B1/B2 no-unexpected-B4-field tests.
* seed-record conversion tests.
* provenance consistency tests.
* atomic JSON write tests.
* existing manifest fixture tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing manifests remain loadable.
* Partial output cannot be accepted as complete.
* Writes must remain atomic or be verified equivalent.
* Resume logic must reject:

  * mismatched identity;
  * mismatched seed provenance;
  * malformed manifest;
  * inconsistent marker state;
  * incomplete result rows.

#### 13. Documentation and Terminology Requirements

Document:

* runtime result versus persisted row;
* per-run manifest versus bounded-sweep manifest;
* generic provenance versus CP2 provenance;
* serialization boundary;
* transport boundary;
* compatibility behavior for optional B4 fields.

#### 14. Acceptance Criteria

* Every persisted CP2 model has one explicit conversion owner.
* Generic transport is not duplicated without justification.
* Existing schemas remain stable.
* Manifest round-trips preserve scientific identity, seeds, metrics, and B4 semantics.
* Resume safety rejects malformed and partial outputs.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * conversion ownership map.
     * one verified assembler per persisted representation.
     * no metric recomputation in serialization.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * manifests preserve CP2 identity, seed, policy, B4, and metric semantics.
     * validation, reporting, CLI, and resume consume compatible schemas.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * round-trip, corrupt-manifest, atomic-write, B4, and provenance tests pass.
     * historical fixtures remain valid.
     * documentation maps all conversion boundaries.

#### 16. Completion Evidence Required

* Manifest conversion map.
* JSON transport ownership map.
* Passing schema and round-trip suite.
* historical artifact compatibility evidence.
* explicit optional-field compatibility decision.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * fields are lost;
  * B4 semantics are flattened;
  * provenance changes;
  * old manifests cannot load;
  * JSON/hashes become incompatible.
* Defer if:

  * source verification proves schema consumers depend on undocumented ordering or omitted-field behavior.

---

### TKT-007 — Establish One Persisted Score-Schema Interpretation Path and Preserve CP2 Runtime Score Containers

* Status: `PLANNED`
* Priority: `P1`
* Phase:

  * Phase B — Artifact Integrity, Serialization, and Resume Safety
* Root cause:

  * `RC-004`
* Finding references:

  * `FND-010`
* Depends on:

  * `TKT-001`
  * `TKT-005`
  * `TKT-006`
* Blocks:

  * `TKT-008`
  * `TKT-010`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.scoring.schema`
  * `datp.scoring.loading`
  * `datp.scoring.cal_loading`
  * `datp.attacks.real_score_loader`
  * `datp.attacks.score_containers`
* Change classification:

  * `ARCHITECTURE_REFACTOR`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * Medium to high.
* Evidence confidence:

  * Medium.

#### 1. Problem Statement

Generic scoring owns score schema and generic loading modules. CP2 has a separate real-score loader that returns CP2 attack-runtime containers.

The desired outcome is not to merge CP2 runtime containers with generic score schema. The desired outcome is to ensure persisted score schema interpretation has one canonical owner.

#### 2. Evidence and Consolidated Rationale

The inventories show:

* generic scoring includes loading and schema modules;
* CP2 real-score loader reads Parquet files;
* CP2 `ClientScores` and `ScoreCollection` have attack-runtime meaning;
* `"reconstruction_error"` is a named persisted schema vocabulary.

The inventories do not prove duplicate parsing or transformations.

#### 3. Current Intended Contract

* Persisted score schema belongs to generic scoring.
* CP2 runtime score containers remain CP2-specific.
* CP2 must use clean inherited score artifacts.
* Calibration, benign test, and attack test scores must remain separated.
* Reservoir sources must not use test or training score data.

#### 4. Required Outcome

A future implementation must prove one of two safe outcomes:

1. CP2 already delegates score schema interpretation to generic scoring:

   * document the boundary and retain it.

2. CP2 independently parses persisted schema:

   * refactor CP2 to adapt validated generic score records into CP2 runtime containers.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* merge `ClientScores` with persisted score schema;
* change `SCORE_COLUMN`;
* change Parquet paths;
* change calibration/test stages;
* allow test or training data into reservoirs;
* normalize or transform scores differently;
* alter existing score artifact schema;
* introduce a CP2-specific score-column vocabulary.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* generic score loading.
* CP2 score loading.
* Parquet read paths.
* stage selection.
* schema validation.
* conversion to `ClientScores`.
* conversion to `ScoreCollection`.
* reservoir inputs.
* score-manifest validation.
* test fixture score artifacts.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Does CP2 duplicate persisted score parsing or only adapt generic loaded values?

* Evidence required:

  * `load_real_score_collection` implementation.
  * generic loader call graph.
  * Parquet schema validation locations.
  * stage validation locations.
  * score transformations.
  * CP2 and generic error handling.

* Conditions that authorize a code change:

  * CP2 independently reads and validates the same persisted schema.
  * Generic loaders can safely provide required stage data.
  * CP2 adaptation preserves current arrays exactly.

* Conditions that close the ticket with no code change:

  * CP2 loader already delegates parsing and validation to generic scoring.

* Forbidden premature changes:

  * changing score stages;
  * changing score column names;
  * changing score transformations;
  * merging runtime containers with schema types;
  * relaxing calibration/test separation.

* Dependent tickets that must wait:

  * `TKT-008`
  * `TKT-010`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Identify the owner of:

   * Parquet loading;
   * score column validation;
   * stage resolution;
   * path resolution;
   * conversion to arrays.

2. Retain `datp.scoring.schema` as score vocabulary owner.

3. Retain `ClientScores` and `ScoreCollection` as CP2 runtime objects.

4. Where duplication is proven:

   * make generic scoring produce validated score-stage records;
   * make CP2 adapt those validated records into CP2 containers.

5. Add explicit validation:

   * calibration scores populate calibration fields only;
   * benign test scores populate benign test fields only;
   * attack test scores populate attack test fields only;
   * no training or test score source becomes a reservoir.

6. Preserve errors, file paths, and schema compatibility.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* `SCORE_COLUMN` remains canonical.
* `ScoringStage` remains canonical for score stage vocabulary.
* CP2 score containers remain typed.
* No raw `"reconstruction_error"` duplicates may be introduced.
* No new score-schema enum is needed.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Affects:

  * CP2 score loading;
  * artifact layout;
  * reservoir safety;
  * metrics;
  * validation;
  * smoke tests.
* Must precede package dependency cleanup if scoring imports artifacts only for paths.
* Must precede CP2 metric boundary work if generic score records become explicit inputs.

#### 11. Test Plan

* generic score schema tests.
* Parquet loading tests.
* CP2 loader tests.
* stage routing tests.
* calibration/test separation tests.
* score-column compatibility tests.
* missing score-column failure tests.
* malformed Parquet failure tests.
* reservoir-not-test-or-training tests.
* historical score artifact compatibility tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing Parquet score artifacts remain valid.
* Score paths remain unchanged.
* CP2 run manifests continue to identify clean score artifact provenance.
* Resume must reject score artifacts that fail schema/stage validation.

#### 13. Documentation and Terminology Requirements

Document:

* persisted score schema;
* generic score record;
* CP2 runtime score container;
* calibration versus benign test versus attack test;
* source restrictions for reservoirs.

#### 14. Acceptance Criteria

* One persisted score-schema owner exists.
* CP2 remains an explicit consumer/adaptor of generic score schema.
* Score-stage separation is test-verified.
* Existing score artifacts remain compatible.
* No CP2-specific duplicate score column vocabulary exists.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * score schema ownership map.
     * CP2 adaptation map.
     * no schema or stage change.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * generic scoring, CP2 loading, reservoir construction, validation, and artifact layout preserve score separation.
     * no test/training source leaks into attack reservoirs.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * score-loading, stage, schema, and reservoir tests pass.
     * existing Parquet fixtures remain compatible.
     * documentation names each score boundary precisely.

#### 16. Completion Evidence Required

* Score ownership diagram.
* Generic-to-CP2 adapter evidence.
* Passing score schema and stage separation tests.
* historical score artifact compatibility results.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * CP2 receives transformed scores different from current behavior;
  * stage routing changes;
  * reservoir source safety weakens;
  * score artifacts become unreadable.
* Defer if:

  * generic and CP2 loading contracts are proven materially different.

---

### TKT-008 — Verify and Correct Package Dependency Direction Around Artifacts, Evaluation, Scoring, Thresholding, and Validation

* Status: `PLANNED`
* Priority: `P1`
* Phase:

  * Phase C — Runtime Diagnostics and Package-Boundary Hardening
* Root cause:

  * `RC-004`
* Finding references:

  * `FND-011`
  * `FND-017`
* Depends on:

  * `TKT-001`
  * `TKT-005`
  * `TKT-006`
  * `TKT-007`
* Blocks:

  * `TKT-009`
  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.artifacts`
  * `datp.scoring`
  * `datp.evaluation`
  * `datp.thresholding`
  * `datp.validation`
* Change classification:

  * `ARCHITECTURE_REFACTOR`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * Medium.
* Estimated blast radius:

  * High package-level impact.
* Evidence confidence:

  * High for risk; medium for exact required changes.

#### 1. Problem Statement

The static dependency inventory identifies a possible package cycle:

* `artifacts -> evaluation -> scoring -> artifacts`

It also identifies validation responsibilities in artifacts, evaluation, validation, checkpointing, and reporting.

This is a package-boundary concern, not proof of a runtime circular import.

#### 2. Evidence and Consolidated Rationale

The inventory supports an investigation into:

* semantic metric validation inside artifacts;
* score path resolution inside scoring;
* threshold-related dependencies;
* result existence checks;
* cross-artifact validation scope.

The safe objective is not indiscriminate dependency removal. The safe objective is to move each responsibility to the lowest coherent owner.

#### 3. Current Intended Contract

* `datp.artifacts`:

  * paths;
  * names;
  * lifecycle;
  * existence primitives;
  * transport I/O.
* `datp.scoring`:

  * score schema;
  * score loading;
  * score generation.
* `datp.evaluation`:

  * generic metric computation;
  * generic metric payload validation.
* `datp.thresholding`:

  * eligibility;
  * threshold calculation;
  * threshold result formation.
* `datp.validation`:

  * cross-artifact;
  * provenance;
  * scientific protocol;
  * result-level validation.

#### 4. Required Outcome

A future implementation must:

* identify actual dependency causes;
* remove unjustified reverse dependencies;
* preserve all validation behavior;
* prevent generic artifacts from owning scientific metric semantics;
* prevent score loading from owning artifact lifecycle semantics;
* document validation scope per package.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* claim a runtime circular import without proof;
* remove validation because it appears duplicated;
* move scientific metric formulas into artifacts;
* move artifact transport into evaluation;
* create an all-purpose `validation_utils` module;
* change metric schemas;
* weaken artifact completeness checks;
* alter threshold behavior.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* exact imports in:

  * `datp.artifacts`;
  * `datp.scoring`;
  * `datp.evaluation`;
  * `datp.thresholding`;
  * `datp.validation`.
* `results_exist`.
* `validate_metrics_payload`.
* artifact existence behavior.
* score path resolution.
* metrics payload validation.
* checkpoint versus result validation overlap.
* report validation scope.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Which exact module-level imports and behaviors create the package-level cycle risk?

* Evidence required:

  * Actual import statements.
  * runtime import graph.
  * type-only import identification.
  * caller map for `results_exist`.
  * validation function map.
  * package initialization behavior.

* Conditions that authorize a code change:

  * An import exists solely because lower-level packages perform higher-level semantic work.
  * The responsibility can move to a package that already owns the concept.
  * public imports and behavior can remain compatible.

* Conditions that close the ticket with no code change:

  * Imports are type-only, lazy, or intentionally necessary and do not create semantic inversion.
  * validation layers are proven to have distinct scopes.

* Forbidden premature changes:

  * removing imports without relocating behavior;
  * changing metrics validation rules;
  * altering public function behavior;
  * moving arbitrary types into core solely to break imports.

* Dependent tickets that must wait:

  * `TKT-009`
  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Produce a source-level responsibility map for:

   * artifact existence;
   * artifact transport;
   * score loading;
   * metric validation;
   * threshold serialization;
   * cross-artifact validation.

2. Classify every identified validation function as:

   * object/schema;
   * artifact existence;
   * cross-artifact consistency;
   * protocol;
   * checkpoint;
   * report input/output.

3. If `results_exist` performs semantic metric validation:

   * move metric semantic validation to evaluation;
   * retain artifacts existence and lifecycle behavior in artifacts;
   * preserve public API through a compatibility wrapper if needed.

4. If scoring imports artifacts only for path resolution:

   * consider injecting or passing path objects rather than importing higher-level artifact semantics.

5. If thresholding imports evaluation only for metric types:

   * use narrow stable types or forward annotations where safe.
   * do not move unrelated metric code.

6. Add package boundary tests that prohibit:

   * artifacts importing CP2 attacks;
   * core importing higher-level packages;
   * generic artifact transport importing high-level scientific computation.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* No duplicate enums.
* Do not move artifact names into core solely for import convenience.
* Preserve generic result and metric models where currently owned.
* Use typed boundary models instead of raw dictionaries when crossing package layers.
* Do not centralize unrelated constants to solve import direction.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* High impact on:

  * package import behavior;
  * test imports;
  * CLI commands;
  * validation;
  * reporting;
  * artifact existence.
* Must precede CLI/validation responsibility cleanup.
* Must not be combined with B4 or identity changes.

#### 11. Test Plan

* Static import graph tests.
* package import tests.
* `results_exist` behavior tests.
* metrics payload validation tests.
* score loading tests.
* threshold serialization tests.
* checkpoint validation tests.
* cross-artifact validation tests.
* public import/re-export tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Artifact existence behavior must remain compatible.
* A complete artifact must still be detected.
* Invalid metric payloads must still be rejected by the appropriate validator.
* Resume behavior must not become more permissive accidentally.

#### 13. Documentation and Terminology Requirements

Document package scope boundaries:

* artifact existence versus semantic validation;
* generic metric schema validation versus cross-artifact validation;
* checkpoint validation versus experiment validation;
* report validation versus scientific validation.

#### 14. Acceptance Criteria

* No unjustified package-level dependency cycle remains.
* `datp.artifacts` no longer owns generic metric semantics.
* Validation responsibilities have a documented owner and scope.
* Public behavior remains compatible.
* No scientific metric or threshold semantics change.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * source-level dependency map.
     * responsibility relocation map.
     * no unresolved unjustified import path.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * config, artifacts, scoring, evaluation, thresholding, validation, CLI, and reporting still interoperate.
     * protocol and provenance validation remain strict.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * static imports, package imports, artifact existence, metric validation, and cross-artifact tests pass.
     * documentation maps validation scopes.

#### 16. Completion Evidence Required

* Updated dependency diagram.
* validation scope map.
* passing import and integration tests.
* public API compatibility results.
* documented unresolved intentional dependencies, if any.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * artifacts stop detecting valid runs;
  * invalid metrics are accepted;
  * package imports fail;
  * public import paths break.
* Defer if:

  * an import is proven necessary and no lower-level boundary can preserve behavior safely.

---

### TKT-009 — Separate CP2-Specific Report Preparation from Generic Reporting Rendering

* Status: `PLANNED`
* Priority: `P1`
* Phase:

  * Phase C — Runtime Diagnostics and Package-Boundary Hardening
* Root cause:

  * `RC-004`
* Finding references:

  * `FND-012`
* Depends on:

  * `TKT-006`
  * `TKT-008`
* Blocks:

  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.reporting`
  * `datp.attacks`
  * `datp.app.cli.report`
* Change classification:

  * `ARCHITECTURE_REFACTOR`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * Medium.
* Estimated blast radius:

  * Medium.
* Evidence confidence:

  * Medium.

#### 1. Problem Statement

The static package inventory states that `datp.reporting` imports `datp.attacks`.

This may be legitimate if reporting consumes stable CP2 manifest models. It is problematic if generic reporting executes attack logic or depends on mutable attack implementation structures.

#### 2. Evidence and Consolidated Rationale

The inventories establish:

* a generic reporting package;
* a CP2 attacks package;
* generic report commands;
* CP2 manifests and result models.

They do not establish the exact imported symbols.

#### 3. Current Intended Contract

* Generic reporting owns:

  * figures;
  * tables;
  * generic build behavior;
  * generic report validation;
  * rendering.
* CP2 attacks own:

  * CP2 metric semantics;
  * manifest schema;
  * policy-specific result interpretation;
  * B4 decomposition semantics.
* CLI report commands own routing only.

#### 4. Required Outcome

A future implementation must either:

* document the dependency as a stable result-model dependency; or
* invert it so that generic reporting receives normalized report inputs rather than importing CP2 implementation behavior.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* remove CP2 report generation;
* change figure/table output names;
* alter report metrics;
* move CP2 scientific calculations into generic reporting;
* force CP2 manifests into generic evaluation schemas;
* rename report CLI commands without compatibility handling.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* reporting imports from attacks;
* imported types/functions;
* report input models;
* figure generation;
* table generation;
* report validation;
* CLI report routing;
* output directory ownership;
* CP2 manifest readers.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Does reporting import stable CP2 result data or CP2 computation behavior?

* Evidence required:

  * Exact imported symbols.
  * reporting call graph.
  * CP2 report data preparation paths.
  * report test fixtures.
  * CLI report behavior.

* Conditions that authorize a code change:

  * Generic reporting directly invokes CP2 scientific computation.
  * reporting depends on mutable runtime attack objects when stable persisted rows exist.
  * normalized report models can preserve output behavior.

* Conditions that close the ticket with no code change:

  * Reporting imports only stable CP2 manifest schema models and does not execute attack computation.

* Forbidden premature changes:

  * moving B4 semantics into generic reporting;
  * changing report output schemas;
  * changing output directories;
  * changing figure names.

* Dependent tickets that must wait:

  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Classify each reporting-to-attacks import as:

   * stable manifest model;
   * CP2 report adapter;
   * runtime result;
   * computation function;
   * accidental leakage.

2. If only stable manifest models are imported:

   * retain dependency;
   * document it as a compatibility-safe boundary.

3. If attack computation is imported:

   * move CP2 report preparation into a specifically named CP2 adapter under attacks.
   * pass normalized report data to generic reporting.
   * retain generic rendering in reporting.

4. Preserve:

   * figure names;
   * table names;
   * output paths;
   * CLI commands;
   * report field semantics.

5. Add dependency tests preventing generic reporting from importing CP2 computation modules.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Report inputs must be typed.
* B4-specific fields remain CP2-owned.
* Generic reporting must not define duplicate CP2 enums.
* Output file names remain compatibility values.
* Configuration routing remains in CLI/orchestration, not rendering modules.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Affects:

  * reporting;
  * attack manifests;
  * CLI report commands;
  * figures;
  * tables;
  * validation.
* Must follow manifest stabilization.
* Must precede CLI routing cleanup.

#### 11. Test Plan

* Generic reporting tests.
* CP2 report adapter tests.
* figure output-name tests.
* table output-name tests.
* manifest-to-report consistency tests.
* CLI report smoke tests.
* static dependency tests.
* report validation tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Reports must consume current manifest schemas.
* Report generation must reject malformed or partial manifests.
* Existing report output names remain stable.
* Resume behavior must not treat report generation as evidence of run completeness.

#### 13. Documentation and Terminology Requirements

Document:

* CP2 report adapter;
* generic renderer;
* report input boundary;
* CP2-specific B4 decomposition presentation;
* generic versus CP2 report validation.

#### 14. Acceptance Criteria

* Generic reporting does not execute CP2 scientific computation.
* Stable CP2 result consumption is documented.
* Existing report outputs remain compatible.
* CP2 metrics and B4 decomposition remain correctly represented.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * import classification.
     * report adapter boundary.
     * no scientific computation moved into generic rendering.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * manifest inputs, metrics, B4 fields, reporting validation, and CLI routing remain consistent.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * report, figure, table, CLI, and dependency tests pass.
     * output names remain stable.
     * documentation identifies CP2 adapter boundary.

#### 16. Completion Evidence Required

* Reporting dependency decision.
* Report input model map.
* output compatibility test results.
* static dependency test results.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * reports change metric meaning;
  * figures/tables move or rename;
  * B4 decomposition becomes incomplete;
  * generic reporting acquires CP2 scientific logic.
* Defer if:

  * current dependency is proven stable, narrow, and appropriate.

---

### TKT-010 — Consolidate CP2 Policy Dispatch and Clarify Generic-Metric Versus Paired-Attack-Metric Ownership

* Status: `PLANNED`
* Priority: `P0`
* Phase:

  * Phase C — Runtime Diagnostics and Package-Boundary Hardening
* Root cause:

  * `RC-005`
* Finding references:

  * `FND-003`
  * `FND-005`
  * `FND-013`
  * `FND-014`
* Depends on:

  * `TKT-001`
  * `TKT-002`
  * `TKT-003`
  * `TKT-007`
* Blocks:

  * `TKT-011`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.attacks.cell_runner`
  * `datp.attacks.threshold_recompute`
  * `datp.attacks.b4_recompute`
  * `datp.attacks.metric_engine`
  * `datp.evaluation.metrics`
* Change classification:

  * `VALIDATION_HARDENING`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High.
* Evidence confidence:

  * High for required separation; medium for exact dispatch consolidation.

#### 1. Problem Statement

B1, B2, and B4 need distinct computations.

However, the inventories identify:

* `recompute_pair`;
* `_run_policy_pair`;
* B1/B2 pair functions;
* B4 recomputation;
* generic evaluation metrics;
* CP2 metric engine;
* `lock_mu_flag_threshold`;
* `compute_mu_flag_threshold`.

The remediation must avoid both extremes:

* duplicated dispatch and duplicated metrics;
* over-generalization that erases policy-specific behavior.

#### 2. Evidence and Consolidated Rationale

The inventories establish:

* policy-specific implementations exist;
* B4 has unique decomposition types;
* generic evaluation metrics are separate from CP2 metric engine;
* CP2 uses paired delta and AUROC-specific behavior.

The inventory does not prove whether dispatch or metric formulas are currently duplicated.

#### 3. Current Intended Contract

* B1 remains a global/shared threshold policy.
* B2 remains a personalized threshold policy.
* B4 remains a cluster threshold policy with client-effective thresholds and decomposition.
* B3 remains rejected for default CP2 behavior.
* Generic binary metrics remain generic.
* CP2-specific metrics remain:

  * delta tau;
  * fleet FPR;
  * AUROC records;
  * mu-flag logic;
  * blast radius;
  * spillover;
  * paired downstream impact.

#### 4. Required Outcome

A future implementation must create:

* one public CP2 policy-dispatch boundary;
* separate B1/B2/B4 implementations;
* one math owner for mu-flag threshold calculation;
* one explicit boundary between generic metrics and CP2 paired metrics;
* no policy or metric semantics change.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* combine B1/B2/B4 into one formula;
* remove B4 decomposition;
* allow B3;
* change AUROC semantics;
* calculate AUROC from changed threshold outputs;
* move CP2 delta metrics into generic evaluation;
* change mu-flag clean-lock semantics;
* introduce a new clustering method;
* alter policy-specific manifest fields.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* `recompute_pair`;
* `_run_policy_pair`;
* B1/B2 pair computations;
* B4 recomputation;
* all policy branch call sites;
* generic metric calculation;
* CP2 metric engine;
* `lock_mu_flag_threshold`;
* `compute_mu_flag_threshold`;
* AUROC calculations;
* CP2 metric serialization.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Are policy dispatch and metric computation currently duplicated, or are they already layered correctly?

* Evidence required:

  * policy call graph;
  * B1/B2/B4 function callers;
  * mu-flag call graph;
  * generic metric formula usage;
  * CP2 metric formula usage;
  * manifest field assembly.

* Conditions that authorize a code change:

  * Multiple public policy dispatch paths exist.
  * B3 can bypass a canonical rejection boundary.
  * generic metric formulas are duplicated in CP2 without distinct semantics.
  * mu-flag math is duplicated.

* Conditions that close the ticket with no code change:

  * One verified dispatcher already exists.
  * generic and CP2 metric computations are already distinct and non-duplicated.
  * mu-flag math has one owner.

* Forbidden premature changes:

  * changing policy formulas;
  * changing B4 configuration;
  * changing B4 decomposition;
  * changing AUROC calculation;
  * combining result models;
  * changing B3 behavior.

* Dependent tickets that must wait:

  * `TKT-011`

#### 8. Detailed Implementation Plan

1. Confirm whether `recompute_pair` is the sole public CP2 policy dispatcher.

2. Retain:

   * B1/B2 functions in their policy computation module;
   * B4 recomputation and decomposition in B4-specific module.

3. Ensure the dispatcher:

   * accepts canonical `ThresholdPolicy`;
   * validates B3 exclusion;
   * receives typed effective config;
   * routes to separate policy implementations;
   * returns one normalized pair contract with policy-specific metadata preserved.

4. Define generic evaluation boundary:

   * generic binary metrics remain in `datp.evaluation.metrics`.
   * CP2 metric engine consumes generic outputs where appropriate.
   * CP2 computes only paired and attack-specific metrics.

5. Confirm one mathematical owner for mu-flag threshold calculation.

   * `lock_mu_flag_threshold` remains orchestration if it locks clean-condition value.
   * mathematical calculation remains in one dedicated function.

6. Ensure AUROC invariance logic uses unchanged test score inputs only.

7. Preserve all existing result fields and serialization mapping.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* `ThresholdPolicy` remains the canonical policy enum.
* No string-based policy dispatch after canonicalization.
* `B4ClusterConfig` is the CP2 B4 parameter carrier.
* `PolicyPair`, `B4ThresholdPair`, `MetricResult`, and generic evaluation models remain separate.
* Policy-specific metadata must not be erased by a generic wrapper.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Depends on:

  * protocol matrix ownership;
  * B4 config ownership;
  * score schema ownership.
* Affects:

  * metrics;
  * manifests;
  * reporting;
  * validation;
  * bounded sweep execution.
* Must precede orchestration cleanup.

#### 11. Test Plan

* B1 semantic tests.
* B2 semantic tests.
* B4 semantic tests.
* B3 rejection tests.
* policy dispatcher matrix tests.
* B4 decomposition tests.
* B4 deterministic seed tests.
* generic metric equivalence tests.
* CP2 delta metric tests.
* fleet FPR tests.
* AUROC invariance tests.
* mu-flag clean-lock tests.
* metric serialization tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Existing policy fields remain stable.
* B4-specific manifest fields remain complete.
* B1/B2 rows must not falsely imply B4 decomposition.
* Resume must reject results whose policy/configuration combination is invalid.

#### 13. Documentation and Terminology Requirements

Document:

* policy dispatcher;
* B1/B2/B4 distinct scientific behavior;
* generic metric versus CP2 paired metric;
* mu-flag calculation versus clean-condition locking;
* AUROC invariance rationale;
* B3 rejection boundary.

#### 14. Acceptance Criteria

* One verified CP2 dispatch boundary exists.
* B1/B2/B4 remain separately implemented.
* B3 cannot enter default CP2 execution.
* Generic metric computation is not silently duplicated.
* CP2 paired metric behavior remains scientifically equivalent.
* B4 decomposition remains complete and reproducible.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * dispatcher call graph.
     * B3 rejection proof.
     * policy-specific implementation boundaries.
     * mu-flag math ownership proof.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * typed config flows through policy dispatch.
     * generic evaluation and CP2 metric engine preserve distinct scopes.
     * manifests and reports retain policy semantics.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * B1/B2/B4, B3, B4 decomposition, AUROC, mu-flag, and serialization tests pass.
     * documentation states policy boundaries accurately.

#### 16. Completion Evidence Required

* Policy dispatcher map.
* metric ownership map.
* B4 decomposition regression results.
* AUROC invariance regression results.
* B3 rejection evidence.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * B1/B2/B4 thresholds change;
  * B4 decomposition changes;
  * B3 becomes permitted;
  * AUROC changes;
  * mu-flag semantics change.
* Defer if:

  * source inspection shows no duplicate dispatch or formula ownership.

---

### TKT-011 — Separate CP2 Sweep Execution, CLI Routing, Validation Scope, and Resume Behavior into Explicit Operational Boundaries

* Status: `PLANNED`
* Priority: `P0`
* Phase:

  * Phase D — CLI, Orchestration, Validation, and Operational Observability
* Root cause:

  * `RC-006`
  * `RC-004`
* Finding references:

  * `FND-015`
  * `FND-016`
  * `FND-017`
* Depends on:

  * `TKT-001`
  * `TKT-002`
  * `TKT-004`
  * `TKT-005`
  * `TKT-006`
  * `TKT-008`
  * `TKT-009`
  * `TKT-010`
* Blocks:

  * `TKT-012`
* May run in parallel with:

  * None.
* Ownership:

  * `datp.attacks.bounded_sweep_matrix`
  * `datp.attacks.bounded_sweep_cell`
  * `datp.attacks.bounded_sweep_run`
  * `datp.app.cli`
  * `datp.validation`
  * `datp.artifacts.lifecycle`
* Change classification:

  * `RUNTIME_DIAGNOSTICS`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * High.
* Estimated blast radius:

  * High.
* Evidence confidence:

  * High for overlap; medium for exact code changes.

#### 1. Problem Statement

The bounded-sweep lifecycle spans:

* matrix enumeration;
* single-cell execution;
* run-level orchestration;
* manifest assembly;
* persistence;
* CLI routing;
* validation;
* status and resume behavior.

The inventories also identify repeated internal CLI command names and multiple validation packages.

The remediation goal is to make each operational layer explicit without changing public command behavior or scientific execution.

#### 2. Evidence and Consolidated Rationale

The inventories identify:

* `enumerate_bounded_sweep_matrix`;
* `enumerate_full_sweep_matrix`;
* `run_sweep_cell`;
* `run_nbaiot_bounded_sweep`;
* `run_bounded_sweep`;
* CLI `preview`, `dry_run`, `smoke`, `status`;
* artifact lifecycle;
* validation packages and functions.

The inventories do not establish actual Typer registration or hidden I/O in cell execution.

#### 3. Current Intended Contract

The intended operational layering is:

* matrix:

  * deterministic condition enumeration;
* cell execution:

  * pure scientific execution for one condition;
* sweep orchestration:

  * clean-score resolution;
  * deterministic iteration;
  * result aggregation;
  * manifest construction;
  * persistence boundary;
* CLI:

  * parsing;
  * config resolution;
  * command routing;
  * user-facing output;
  * exception translation;
* validation:

  * schema, artifact, provenance, cross-artifact, protocol, and report scopes;
* lifecycle:

  * completeness and resume safety.

#### 4. Required Outcome

A future implementation must produce:

* one explicit execution path for:

  * preview;
  * dry-run;
  * smoke;
  * bounded run;
  * status;
  * validation;
  * resume;
* shared matrix and guardrail behavior across command modes;
* thin CLI modules;
* scoped validation ownership;
* safe partial-run detection.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* rename public commands without compatibility handling;
* alter matrix conditions;
* change dry-run or smoke semantics;
* duplicate matrix construction in CLI;
* allow CLI-local scientific defaults;
* allow CLI-local manifest construction;
* weaken validation;
* change resume semantics without artifact compatibility tests;
* batch CP2 tickets or matrix cells through unverified shortcuts.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* Typer registrations;
* command group structure;
* function-to-command mappings;
* CLI direct writes;
* CLI direct matrix creation;
* dry-run path;
* smoke path;
* run path;
* status path;
* validation path;
* lifecycle marker interpretation;
* resume logic;
* bounded sweep orchestration;
* cell execution side effects.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Do CLI, smoke, dry-run, run, validation, and status paths use the same underlying protocol definitions and artifact lifecycle rules?

* Evidence required:

  * Typer registration map.
  * command call graph.
  * matrix invocation map.
  * guardrail invocation map.
  * manifest write path.
  * lifecycle/resume call graph.
  * validation scope map.

* Conditions that authorize a code change:

  * CLI performs scientific work or artifact assembly directly.
  * dry-run/smoke/run use independently constructed matrix or protocol values.
  * validation scopes overlap materially.
  * status and resume use inconsistent marker interpretation.

* Conditions that close the ticket with no code change:

  * Command boundaries are already thin.
  * all modes consume one orchestration and lifecycle path.
  * validation scopes are already distinct and documented.

* Forbidden premature changes:

  * renaming command groups;
  * changing command options;
  * changing output paths;
  * changing matrix order;
  * changing resume behavior;
  * removing validation checks.

* Dependent tickets that must wait:

  * `TKT-012`

#### 8. Detailed Implementation Plan

1. Build a command responsibility map:

   * command name;
   * Typer group;
   * public CLI path;
   * configuration input;
   * orchestration target;
   * artifact outputs;
   * validation target;
   * status behavior.

2. Rename internal Python functions only if:

   * Typer external names remain stable;
   * ambiguity materially harms maintainability.

3. Require CLI modules to:

   * parse;
   * normalize to enums/types;
   * resolve config;
   * call orchestration;
   * display results;
   * translate exceptions.

4. Move or preserve scientific work in:

   * matrix module;
   * cell runner;
   * sweep runner;
   * policy dispatcher;
   * artifact/manifest modules.

5. Make dry-run, smoke, and run share:

   * same validated matrix;
   * same protocol config;
   * same guardrails;
   * explicit mode-specific execution depth only.

6. Define validation scopes:

   * artifacts:

     * presence/lifecycle;
   * evaluation:

     * generic metrics schema;
   * validation:

     * cross-artifact, provenance, protocol;
   * checkpointing:

     * checkpoint-specific;
   * reporting:

     * report input/output.

7. Make status and resume consume lifecycle ownership rather than custom marker checks.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* CLI inputs normalize to canonical enums.
* CLI must not build raw condition dictionaries.
* Typed request/specification models must be used where available.
* No duplicate CLI-specific fraction grid, policy tuple, or seed default.
* CLI help text must distinguish:

  * generic preview;
  * checkpoint preview;
  * poison preview;
  * repository status;
  * checkpoint status.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Affects:

  * all CP2 command paths;
  * manifests;
  * artifacts;
  * validation;
  * reporting;
  * resume;
  * logs.
* Cannot run in parallel with unresolved identity, config, lifecycle, manifest, or policy changes.
* Must precede cleanup ticket because architecture tests need the final operational boundaries.

#### 11. Test Plan

* CLI registration tests.
* CLI help text tests.
* CLI preview tests.
* CLI dry-run tests.
* CLI smoke tests.
* CLI bounded-run tests.
* CLI error-path tests.
* command-to-orchestrator delegation tests.
* matrix equivalence tests across modes.
* guardrail equivalence tests across modes.
* status tests.
* resume tests.
* partial/corrupt artifact tests.
* validation-scope tests.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Dry-run must not create run artifacts unless current contract explicitly requires it.
* Smoke must not silently use a different matrix.
* Bounded run must create expected manifests and lifecycle markers.
* Status must distinguish:

  * absent;
  * in-progress;
  * done;
  * aborted;
  * corrupt.
* Resume must reject malformed, mismatched, or partial outputs.
* CLI must not bypass manifest validation.

#### 13. Documentation and Terminology Requirements

Document:

* command groups;
* external command names;
* internal orchestration targets;
* preview/dry-run/smoke/run distinction;
* validation scopes;
* lifecycle states;
* resume rules;
* CP2 mode limitations.

#### 14. Acceptance Criteria

* CLI remains thin.
* All command modes share canonical protocol behavior.
* Validation responsibilities are explicitly documented and non-overlapping where possible.
* Status and resume use lifecycle ownership.
* Public command compatibility is preserved.
* No CP2 scientific behavior moves into CLI.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * command responsibility map.
     * CLI-to-orchestration mapping.
     * no scientific computation or manifest assembly remains in CLI without explicit justification.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * config, matrix, guardrails, policy dispatch, artifacts, manifests, validation, and reporting use aligned protocol values.
     * smoke/dry-run/run remain equivalent in shared semantics.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * CLI, status, resume, validation, and artifact tests pass.
     * malformed outputs are rejected.
     * command documentation matches actual behavior.

#### 16. Completion Evidence Required

* CLI command map.
* validation-scope map.
* status/resume state matrix.
* passing command, matrix, lifecycle, and validation test results.
* public command compatibility evidence.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * command interfaces break;
  * dry-run/smoke/run produce different matrix semantics;
  * CLI changes scientific defaults;
  * resume accepts incomplete results;
  * validation weakens.
* Defer if:

  * Typer registration or external command compatibility cannot be preserved safely.

---

### TKT-012 — Consolidate Test-Support Ownership, Preserve Semantic Architecture Tests, and Resolve the Status of `datp.analyses`

* Status: `PLANNED`
* Priority: `P2`
* Phase:

  * Phase E — Test Support, Documentation, and Controlled Cleanup
* Root cause:

  * `RC-007`
* Finding references:

  * `FND-018`
  * `FND-020`
  * `FND-021`
* Depends on:

  * `TKT-001`
  * `TKT-008`
  * `TKT-011`
* Blocks:

  * Final program audits.
* May run in parallel with:

  * None.
* Ownership:

  * `datp.testsupport`
  * architecture test suite
  * package-level import tests
* Change classification:

  * `TEST_COVERAGE`
* Implementation mode:

  * `VERIFY_THEN_DECIDE`
* Scientific-contract sensitivity:

  * Medium.
* Estimated blast radius:

  * Low to medium.
* Evidence confidence:

  * Medium.

#### 1. Problem Statement

The repository has:

* dedicated test-support utilities;
* multiple package-specific test suites;
* architecture-focused tests;
* an explicitly empty `datp.analyses` package;
* a broad but intentionally leaf-layer `datp.core`.

The remediation must avoid deleting useful tests, over-centralizing fixtures, or splitting `core` without evidence.

#### 2. Evidence and Consolidated Rationale

The inventories establish:

* `testsupport` owns synthetic score, checkpoint, and smoke helpers.
* architecture tests already exist for canonical ownership, dataclass architecture, model boundaries, and scientific policy leaks.
* `analyses` is empty.
* `core` has broad responsibility but no internal package dependencies.

The inventories do not establish actual fixture duplication, runtime imports of testsupport, or external imports of analyses.

#### 3. Current Intended Contract

* `testsupport` is test-only.
* Runtime packages must not depend on test support.
* Architecture tests must protect:

  * dependency direction;
  * canonical ownership;
  * scientific locks;
  * CP2 scope.
* `core` remains low-level and modular.
* `analyses` must either:

  * be removed after verification;
  * or be retained as documented compatibility namespace.

#### 4. Required Outcome

A future implementation must:

* centralize only genuinely reused test fixture construction;
* retain policy-specific test fixtures where they encode unique scientific cases;
* preserve semantic architecture tests;
* prevent runtime imports of `testsupport`;
* decide the fate of `datp.analyses` based on evidence;
* avoid a broad `core` split.

#### 5. Explicit Non-Goals and Prohibited Changes

Do not:

* delete repetitive tests merely because they look similar;
* centralize scientifically distinct B1/B2/B4 test scenarios into an opaque fixture;
* import testsupport from runtime packages;
* split `datp.core` into top-level packages without evidence;
* repurpose `analyses` as a miscellaneous module;
* delete `analyses` before verifying imports, package metadata, documentation, and tests.

#### 6. Conceptual Areas and Future Implementation Surfaces to Verify

Verify:

* local synthetic score fixture definitions;
* test support imports;
* runtime imports;
* architecture test assertions;
* package import tests;
* public re-exports;
* `analyses` references in:

  * source;
  * tests;
  * package metadata;
  * CLI;
  * documentation;
  * external scripts if included in repository scope.

#### 7. Detailed Future Verification Steps

#### Decision Gate

* Question to verify:

  * Which test helpers are genuinely reused and which encode distinct scientific scenarios?

* Evidence required:

  * Test fixture inventory.
  * fixture call sites.
  * runtime import scan.
  * architecture test assertions.
  * `analyses` reference scan.

* Conditions that authorize a code change:

  * Equivalent fixture construction is duplicated across multiple tests.
  * A fixture has stable test-only semantics.
  * `analyses` is proven unused.
  * architecture tests are proven to assert incidental paths rather than semantic boundaries.

* Conditions that close the ticket with no code change:

  * Fixtures are intentionally scenario-specific.
  * `analyses` is a public compatibility namespace.
  * current architecture tests already assert semantic contracts.

* Forbidden premature changes:

  * deleting tests;
  * moving runtime helper behavior into testsupport;
  * deleting analyses;
  * broadly splitting core;
  * weakening architecture tests.

* Dependent tickets that must wait:

  * Final program audit only.

#### 8. Detailed Implementation Plan

1. Inventory test fixture construction for:

   * synthetic client scores;
   * eligible client cases;
   * pending client cases;
   * degenerate-tail cases;
   * fake checkpoint metrics;
   * smoke execution cases.

2. Move only reusable fixture construction into:

   * `datp.testsupport.synthetic_scores`;
   * `datp.testsupport.checkpoint_protocol`;
   * `datp.testsupport.smoke_harness`.

3. Keep local fixtures where they encode:

   * policy-specific semantics;
   * edge cases;
   * protocol-specific failure states;
   * unique artifact arrangements.

4. Add static check preventing runtime package imports of `datp.testsupport`.

5. Review architecture tests:

   * retain semantic boundary tests;
   * replace path-location assertions only if equivalent semantic assertions are added first.

6. Verify `datp.analyses`:

   * if unused, remove in a dedicated small cleanup change;
   * if used, retain and document the compatibility purpose;
   * do not add unrelated modules to it.

7. Preserve `datp.core` as low-level leaf package and add boundary tests rather than broad restructure.

#### 9. Enum, Dataclass, Configuration, Constant, and Raw-String Requirements

* Test fixtures must use canonical enums and typed models.
* No test-only duplicate enum may represent production domain vocabulary.
* Synthetic fixture defaults must document scientific meaning.
* Tests must not introduce raw protocol values where canonical constants exist.
* No runtime configuration values may be hidden inside testsupport.

#### 10. Dependency, Compatibility, and Change-Impact Analysis

* Affects:

  * unit tests;
  * integration tests;
  * architecture tests;
  * package imports;
  * potential public namespace compatibility.
* Must follow final ownership and package boundary changes.
* Low production artifact risk but medium scientific regression-detection risk.

#### 11. Test Plan

* testsupport import tests.
* runtime-no-testsupport-import test.
* fixture determinism tests.
* synthetic score semantic tests.
* attack integration tests.
* checkpoint fixture tests.
* architecture test suite.
* package import suite.
* analyses import/reference tests.
* stale reference scan.

#### 12. Artifact, Manifest, Serialization, and Resume Requirements

* Test support must preserve existing artifact fixture schema.
* No test helper may silently alter manifest or path contracts.
* Test fixtures for partial/corrupt outputs must remain explicit and reproducible.

#### 13. Documentation and Terminology Requirements

Document:

* testsupport public test-only API;
* runtime import prohibition;
* fixture semantic categories;
* architecture test purpose;
* `analyses` final status;
* `core` leaf-layer rationale.

#### 14. Acceptance Criteria

* Reused test helpers have one test-only owner.
* Runtime code does not import testsupport.
* Architecture tests protect meaningful semantics.
* `analyses` has a documented final state.
* `core` remains a low-level leaf package.
* No meaningful test coverage is removed.

#### 15. Three Required Post-Ticket Audits

1. **Audit 1 — Implementation and Contract Correctness**

   * Evidence required:

     * fixture ownership map.
     * runtime import scan.
     * analyses usage decision.
     * preserved architecture test purpose.

2. **Audit 2 — Cross-Package and Protocol Safety**

   * Evidence required:

     * synthetic CP2 fixtures retain eligibility, tail, pairing, and score-stage semantics.
     * architecture tests preserve protocol locks.

3. **Audit 3 — Tests, Artifacts, and Documentation Integrity**

   * Evidence required:

     * full test suite passes.
     * fixture determinism tests pass.
     * stale-reference scans pass.
     * testsupport and analyses documentation are current.

#### 16. Completion Evidence Required

* Fixture duplication assessment.
* Runtime-import boundary report.
* architecture-test review report.
* `analyses` decision record.
* Passing full test suite.

#### 17. Rollback, Regression, and Protocol-Drift Risks

* Roll back if:

  * test fixtures lose policy-specific semantics;
  * runtime imports testsupport;
  * package imports break;
  * architecture tests weaken scientific protection.
* Defer analyses removal if:

  * any public import or packaging reference remains.

---

## 9. Cross-Ticket Dependencies and Compatibility Rules

### 9.1 Mandatory Sequencing Rules

* `TKT-001 MUST_PRECEDE` every other ticket.

  * Reason:

    * CP2 behavioral, artifact, and protocol locks must exist before refactoring.

* `TKT-002 MUST_PRECEDE TKT-003`.

  * Reason:

    * B4 parameters cannot be centralized until the broader CP2 protocol-value ownership model is defined.

* `TKT-002 MUST_PRECEDE TKT-004`.

  * Reason:

    * canonical identity must use canonical enums, seeds, fractions, source, objective, and scope vocabulary.

* `TKT-003 MUST_PRECEDE TKT-010`.

  * Reason:

    * policy dispatch must receive typed B4 configuration before its boundary is consolidated.

* `TKT-004 MUST_PRECEDE TKT-005`.

  * Reason:

    * CP2 paths must derive from canonical identity before layout ownership is stabilized.

* `TKT-004 MUST_PRECEDE TKT-006`.

  * Reason:

    * manifests must derive identity from canonical representation.

* `TKT-005 MUST_PRECEDE TKT-006`.

  * Reason:

    * lifecycle and path ownership must be stable before manifest and resume behavior is consolidated.

* `TKT-006 MUST_PRECEDE TKT-009`.

  * Reason:

    * report preparation must consume stable normalized manifest structures.

* `TKT-007 MUST_PRECEDE TKT-008`.

  * Reason:

    * score-schema ownership must be clarified before fixing package dependencies around scoring.

* `TKT-008 MUST_PRECEDE TKT-009`.

  * Reason:

    * reporting dependency cleanup depends on clarified package boundaries.

* `TKT-010 MUST_PRECEDE TKT-011`.

  * Reason:

    * CLI and sweep orchestration must call stable policy dispatch and metric boundaries.

* `TKT-011 MUST_PRECEDE TKT-012`.

  * Reason:

    * architecture tests and test support should reflect final operational boundaries.

### 9.2 Shared-Design Decisions

The following relationships require shared design decisions:

* `TKT-002` and `TKT-003`

  * `REQUIRES_SHARED_DESIGN_DECISION`
  * CP2 protocol configuration must distinguish generic threshold configuration from fixed CP2 B4 behavior.

* `TKT-004` and `TKT-005`

  * `REQUIRES_SHARED_DESIGN_DECISION`
  * Identity-to-path projection must preserve artifact compatibility.

* `TKT-004` and `TKT-006`

  * `REQUIRES_SHARED_DESIGN_DECISION`
  * Identity-to-manifest flattening must preserve field names and grouping semantics.

* `TKT-005` and `TKT-011`

  * `REQUIRES_SHARED_DESIGN_DECISION`
  * lifecycle mapping must support CLI status and resume behavior.

* `TKT-008` and `TKT-011`

  * `REQUIRES_SHARED_DESIGN_DECISION`
  * validation ownership must align with CLI behavior and artifact existence checks.

* `TKT-009` and `TKT-011`

  * `REQUIRES_SHARED_DESIGN_DECISION`
  * CLI report routing must use normalized report input models.

### 9.3 May-Run-in-Parallel Rules

No implementation tickets in this plan are approved for parallel execution.

Reason:

* all tickets affect overlapping protocol, identity, artifact, package, or validation boundaries;
* parallel changes would make it difficult to attribute behavior drift;
* the backlog explicitly requires one-ticket-at-a-time execution.

### 9.4 Mutually Exclusive Decisions

The following outcomes are mutually exclusive and must not both be implemented:

* `datp.analyses`:

  * remove as unused;
  * retain as documented compatibility namespace.

* B4 configuration:

  * merge generic and CP2 B4 config;
  * retain separate models with an explicit bridge.
  * Only one may be chosen after source verification.

* reporting dependency:

  * retain narrow dependency on stable CP2 manifest models;
  * replace with CP2 report adapter.
  * Both must not be implemented simultaneously.

* score loading:

  * retain documented generic-to-CP2 adapter already present;
  * introduce new adapter due duplication.
  * Only one outcome is valid.

### 9.5 Compatibility Rules

1. Existing artifact paths are compatibility contracts.
2. Existing output root remains unchanged.
3. Existing manifest keys remain unchanged unless a migration is explicitly approved.
4. Existing enum serialized values remain unchanged.
5. Existing CLI command paths remain unchanged unless compatibility aliases exist.
6. Existing public imports remain stable through re-export or deprecation strategy where necessary.
7. Historical artifacts remain readable by default.
8. Compatibility aliases must have one documented expiration condition.
9. A compatibility alias must not become a second canonical owner.
10. No artifact migration is permitted without:

    * old-to-new mapping;
    * rollback strategy;
    * compatibility tests;
    * manifest provenance decision.

---

## 10. Per-Ticket Audit Requirements

Every ticket that may produce code changes must complete exactly three post-ticket audits.

### Audit 1 — Implementation and Contract Correctness

Every ticket must verify:

* the implemented change matches the ticket;
* canonical ownership is preserved;
* public interfaces remain coherent;
* enums, dataclasses, configuration, constants, and raw strings are handled according to their defined boundary;
* error handling remains actionable;
* no unrelated behavior changed;
* no new generic dumping-ground module was introduced;
* no duplicate owner was created.

Required evidence:

* source-level ownership map;
* before/after interface map;
* explicit compatibility note;
* focused test results;
* identified non-goals checked against changed files.

### Audit 2 — Cross-Package and Protocol Safety

Every ticket must verify:

* configuration propagation;
* enum normalization;
* validation boundary behavior;
* CLI/public interface compatibility;
* artifact and manifest compatibility;
* result loading and reporting compatibility;
* resume behavior;
* reproducibility;
* paired-run semantics;
* B3 exclusion;
* B4 semantics where relevant;
* no CP2 scope expansion.

Required evidence:

* cross-package call map;
* protocol invariant test results;
* manifest/path compatibility results;
* dependency graph delta;
* explicit statement of unaffected scientific contracts.

### Audit 3 — Tests, Artifacts, and Documentation Integrity

Every ticket must verify:

* focused unit tests pass;
* negative tests exist;
* integration tests are run where boundaries cross packages;
* artifacts and manifests remain valid;
* malformed or partial output cannot be accepted as complete;
* documentation matches actual behavior;
* stale names, raw strings, comments, and terminology are removed or explicitly retained for compatibility;
* architecture tests are updated only after equivalent semantic protection exists.

Required evidence:

* test report;
* artifact fixture report;
* manifest round-trip report where relevant;
* stale-reference scan;
* documentation review checklist;
* unresolved limitation list.

---

## 11. Final Program Audit Requirements

### Final Audit 1 — Architecture, Ownership, and Duplication

Check for:

* duplicated responsibilities;
* unclear package ownership;
* duplicated validation;
* duplicated utilities;
* circular dependencies;
* stale abstractions;
* unnecessary wrappers;
* enum duplication;
* raw-string drift;
* generic packages importing CP2 computation without explicit justification;
* CP2-specific modules absorbing generic infrastructure;
* duplicated artifact writers;
* duplicated path construction.

Required evidence:

* final package dependency map;
* final ownership register;
* duplicate symbol and import report;
* documented intentional separations.

### Final Audit 2 — Enums, Dataclasses, Configuration, Constants, and Serialization

Check for:

* missing or duplicate enums;
* raw strings where canonical enums should be used;
* hidden defaults;
* configuration drift;
* magic values;
* stale candidate lists;
* schema mismatches;
* invalid serialization;
* missing provenance;
* manifest inconsistency;
* B4 parameter drift;
* seed-pool drift;
* fraction-grid drift;
* generic/CP2 config confusion.

Required evidence:

* effective config report;
* enum serialization report;
* manifest schema report;
* constant ownership register;
* stale direct-import scan.

### Final Audit 3 — Integration, Artifacts, and Resume Safety

Check:

* public-interface to configuration propagation;
* matrix construction;
* validation;
* runtime behavior;
* artifact lifecycle;
* manifests;
* stale-result detection;
* partial-run detection;
* resume behavior;
* result loading;
* report generation;
* actionable failure diagnostics;
* score-stage separation.

Required evidence:

* CLI integration test report;
* lifecycle state matrix;
* resume test report;
* artifact fixture compatibility report;
* manifest round-trip report;
* report generation compatibility report.

### Final Audit 4 — Scientific, Experimental, and Reproducibility Contract

Check:

* calibration-channel-only boundary;
* clean-versus-poisoned pairing;
* seed separation;
* baseline eligibility;
* metric definitions;
* B1/B2/B4 policy semantics;
* B3 exclusion;
* B4 clustering parameters;
* B4 effective threshold interpretation;
* B4 decomposition;
* unchanged test data for AUROC;
* artifact provenance;
* absence of unauthorized scope expansion;
* no accidental model, training, aggregation, privacy, deployment, or dataset changes.

Required evidence:

* CP2 contract suite results;
* policy equivalence results;
* B4 decomposition results;
* AUROC invariance results;
* clean/poisoned pairing report;
* effective protocol configuration report.

### Final Audit 5 — Code Quality, Tests, and Documentation

Check:

* naming;
* comments;
* docstrings;
* AI-looking filler wording;
* dead code;
* duplicated helpers;
* misleading documentation;
* test quality;
* untracked compatibility changes;
* overengineering;
* accidental performance regressions;
* stale temporary naming;
* unexplained CP2 references in generic code;
* unverified TODOs that affect protocol behavior.

Required evidence:

* stale naming scan;
* code-quality review;
* documentation consistency review;
* architecture test review;
* test-support boundary report;
* final deferred-work register.

---

## 12. Explicitly Rejected Recommendations

### REJ-001 — Merge All CP2 Identity, Path, Manifest, Runtime, and Seed Models into One Universal Model

* Source finding:

  * `FND-001`
  * `FND-022`

* Rejected recommendation:

  * Replace `TrainingCellId`, `BaselineRunId`, `CellId`, `SweepCellSpec`, `SweepCellResult`, `SeedRecord`, and `BoundedSweepResultRow` with one global model.

* Why it is rejected:

  * These models represent different lifecycle and boundary responsibilities.
  * A universal model would mix:

    * training identity;
    * baseline identity;
    * CP2 condition;
    * seed derivation;
    * artifact paths;
    * runtime result;
    * manifest serialization.

* Relevant binding contract:

  * Preserve distinct generic training identity and CP2 attack identity.
  * Preserve flat manifest compatibility.
  * Preserve path compatibility.

* Narrower concern that remains valid, if any:

  * CP2 condition and run identity need one canonical semantic owner.

* Related verification-gated ticket, if any:

  * `TKT-004`

* Conditions under which it could become future work:

  * None within this remediation scope.

### REJ-002 — Merge `ArtifactLayout` and `PoisonLayout` into One Universal Artifact Layout

* Source finding:

  * `FND-006`

* Rejected recommendation:

  * Replace generic and CP2 artifact layouts with one universal layout object.

* Why it is rejected:

  * They manage distinct artifact families.
  * Generic training artifacts and CP2 poisoning artifacts have different lifecycle, path, and manifest needs.
  * A shared universal layout would create CP2 leakage into generic infrastructure.

* Relevant binding contract:

  * Existing artifact family boundaries.
  * Existing CP2 output paths.

* Narrower concern that remains valid, if any:

  * CP2 path identity should derive from canonical CP2 identity.

* Related verification-gated ticket, if any:

  * `TKT-005`

* Conditions under which it could become future work:

  * None within this remediation scope.

### REJ-003 — Move Every Scientific Constant into YAML

* Source finding:

  * `FND-004`

* Rejected recommendation:

  * Convert all code-owned CP2 constants into editable YAML defaults.

* Why it is rejected:

  * CP2 scientific values include protocol locks.
  * Editable defaults could silently alter:

    * seed pools;
    * B4 behavior;
    * threshold quantile;
    * matrix conditions;
    * fraction grids;
    * trim fractions.

* Relevant binding contract:

  * Scientific protocol lock.
  * Reproducibility.
  * paired comparison consistency.

* Narrower concern that remains valid, if any:

  * Effective configuration must be typed, explicit, validated, and serializable.

* Related verification-gated ticket, if any:

  * `TKT-002`
  * `TKT-003`

* Conditions under which it could become future work:

  * Only under an explicitly approved experiment-protocol revision.

### REJ-004 — Merge B1, B2, and B4 into a Single Generic Threshold Formula

* Source finding:

  * `FND-013`

* Rejected recommendation:

  * Replace B1/B2/B4 implementations with one abstract threshold routine.

* Why it is rejected:

  * B4 has unique clustering, effective-threshold, and decomposition semantics.
  * B1 and B2 encode distinct threshold-scope behavior.
  * A generic formula would risk scientific abstraction drift.

* Relevant binding contract:

  * B1/B2/B4 policy meaning.
  * B4 decomposition.
  * B3 exclusion.

* Narrower concern that remains valid, if any:

  * One policy dispatcher may select among separate implementations.

* Related verification-gated ticket, if any:

  * `TKT-010`

* Conditions under which it could become future work:

  * None within CP2 remediation.

### REJ-005 — Rename or Move `CALIBRATION_POISONING_OUTPUT_ROOT` During General Refactoring

* Source finding:

  * `FND-006`
  * `FND-007`

* Rejected recommendation:

  * Rename `"conference_calibration_poisoning"` as a cleanup step.

* Why it is rejected:

  * It is an artifact compatibility value.
  * Existing outputs may depend on it.
  * The inventory gives no approved migration strategy.

* Relevant binding contract:

  * Existing output-root compatibility.

* Narrower concern that remains valid, if any:

  * Ensure the string has one owner and no stale duplicate literals.

* Related verification-gated ticket, if any:

  * `TKT-005`

* Conditions under which it could become future work:

  * Separate explicit artifact migration project with old-to-new mapping and rollback plan.

### REJ-006 — Treat Every Repeated Numeric Literal as a Duplicate Constant

* Source finding:

  * `FND-004`
  * `FND-019`

* Rejected recommendation:

  * Merge all instances of:

    * `0.10`;
    * `0.05`;
    * `0.95`;
    * `100`;
    * `42`.

* Why it is rejected:

  * The inventories show same literals in unrelated semantic contexts.

* Relevant binding contract:

  * Scientific parameter ownership and reproducibility.

* Narrower concern that remains valid, if any:

  * Same-concept duplicates must be classified and centralized.

* Related verification-gated ticket, if any:

  * `TKT-002`

* Conditions under which it could become future work:

  * Only after source verification proves same semantic ownership.

### REJ-007 — Delete `datp.analyses` Immediately Because It Is Empty

* Source finding:

  * `FND-020`

* Rejected recommendation:

  * Delete the package without verification.

* Why it is rejected:

  * The inventory does not prove lack of imports, package metadata reference, or public compatibility status.

* Relevant binding contract:

  * Public import compatibility.

* Narrower concern that remains valid, if any:

  * Verify actual consumers and remove only if unused.

* Related verification-gated ticket, if any:

  * `TKT-012`

* Conditions under which it could become future work:

  * After a repository-wide reference and package compatibility check.

### REJ-008 — Split `datp.core` Into Multiple Top-Level Packages Because It Is Broad

* Source finding:

  * `FND-021`

* Rejected recommendation:

  * Split core based on package size or breadth alone.

* Why it is rejected:

  * The inventory supports a leaf-layer core with focused internal modules and no internal package imports.
  * Broad low-level ownership is not itself evidence of a defect.

* Relevant binding contract:

  * Core remains dependency-light and imported by higher layers.

* Narrower concern that remains valid, if any:

  * Ensure core does not gain high-level package dependencies.
  * Keep CP2 low-level primitives explicitly named.

* Related verification-gated ticket, if any:

  * `TKT-012`

* Conditions under which it could become future work:

  * Only if source-level dependency evidence shows core has become a mixed high-level dependency hub.

---

## 13. Deferred and Out-of-Scope Work

### Deferred Item 001 — New Attack Families

* Why it is out of scope:

  * CP2 is calibration-channel poisoning only.

* Separate project or authorization required:

  * New protocol and threat-model approval.

* Why it must not be implemented incidentally:

  * Training-data, model-update, aggregation, backdoor, and general evasion attacks would invalidate the narrow CP2 claim boundary.

* Current contract affected:

  * Calibration-channel-only threat model.

### Deferred Item 002 — New FL Aggregation Methods or Model Personalization

* Why it is out of scope:

  * CP2 preserves inherited model and FedAvg training artifacts.

* Separate project or authorization required:

  * New benchmark protocol and model-training experiment design.

* Why it must not be implemented incidentally:

  * It would change the causal interpretation from threshold-calibration vulnerability to broader FL robustness.

* Current contract affected:

  * Fixed inherited training and model behavior.

### Deferred Item 003 — New Datasets, Journal Regimes, or External Comparators

* Why it is out of scope:

  * CP2 primary scope is N-BaIoT, with optional stretch scope governed separately.

* Separate project or authorization required:

  * CP2 stretch authorization or journal-extension protocol.

* Why it must not be implemented incidentally:

  * New datasets alter client identity, score semantics, paths, eligibility, artifact provenance, and conclusions.

* Current contract affected:

  * N-BaIoT primary-dataset boundary.

### Deferred Item 004 — Formal Privacy Mechanisms

* Why it is out of scope:

  * Privacy mechanisms are excluded from CP2.

* Separate project or authorization required:

  * Privacy protocol, budget definition, overhead study, and threat-model redesign.

* Why it must not be implemented incidentally:

  * It would change both the attack surface and observable data assumptions.

* Current contract affected:

  * Calibration-only attack scope and no-privacy expansion boundary.

### Deferred Item 005 — Hardware, Edge, Deployment, and Communication Benchmarking

* Why it is out of scope:

  * No hardware or deployment claims belong in the current remediation scope.

* Separate project or authorization required:

  * Deployment and system-evaluation protocol.

* Why it must not be implemented incidentally:

  * It requires different assets, metrics, environmental assumptions, and conclusions.

* Current contract affected:

  * CP2 conference-sized scope.

### Deferred Item 006 — Artifact Root Renaming or Historical Artifact Migration

* Why it is out of scope:

  * Existing output roots and paths are compatibility-sensitive.

* Separate project or authorization required:

  * Dedicated migration plan.

* Why it must not be implemented incidentally:

  * Migration risk is unrelated to the verified remediation objectives.

* Current contract affected:

  * Artifact discoverability and manifest provenance.

### Deferred Item 007 — Broad Rewrite of Package Structure

* Why it is out of scope:

  * The inventories support incremental remediation, not a rewrite.

* Separate project or authorization required:

  * Architecture redesign initiative with full source-level evidence.

* Why it must not be implemented incidentally:

  * Broad rewrite would invalidate compatibility assumptions and increase scientific drift risk.

* Current contract affected:

  * All package, artifact, and protocol boundaries.

---

## 14. Resume and Status Management Rules

Use only the following statuses:

* `PLANNED`
* `NEEDS_VERIFICATION`
* `IN_PROGRESS`
* `BLOCKED`
* `IMPLEMENTED`
* `AUDITED`
* `SUPERSEDED`
* `REJECTED`
* `DEFERRED`

Apply these rules strictly:

1. Work one ticket at a time.

2. Do not batch tickets.

3. Do not jump ahead of unresolved dependencies.

4. Complete all three post-ticket audits before starting the next dependent ticket.

5. Preserve completion evidence for every ticket:

   * scope decision;
   * changed conceptual owners;
   * tests run;
   * artifact compatibility evidence;
   * manifest compatibility evidence;
   * protocol impact assessment;
   * rollback decision.

6. Update status accurately:

   * `PLANNED`:

     * no work started.
   * `NEEDS_VERIFICATION`:

     * source evidence required before implementation.
   * `IN_PROGRESS`:

     * source inspection or implementation actively underway.
   * `BLOCKED`:

     * a design decision cannot be resolved from approved evidence.
   * `IMPLEMENTED`:

     * implementation work complete but audits pending.
   * `AUDITED`:

     * all three required post-ticket audits complete.
   * `SUPERSEDED`:

     * replaced by a stronger approved ticket or decision.
   * `REJECTED`:

     * explicitly not implemented because it conflicts with contract or evidence.
   * `DEFERRED`:

     * valid future work but outside scope.

7. Stop and mark a ticket `BLOCKED` when:

   * source verification reveals an unresolved compatibility contract;
   * an artifact migration is required but not approved;
   * an external public import cannot be preserved;
   * a scientific protocol decision cannot be made from approved evidence;
   * the actual code contradicts the inventory in a materially important way.

8. Resume from the first ticket that is not:

   * `AUDITED`;
   * `REJECTED`;
   * `SUPERSEDED`;
   * `DEFERRED`.

9. Re-run only impacted audits after resuming, but always re-run:

   * protocol safety audit;
   * artifact/manifest integrity audit;
   * tests directly affected by resumed work.

10. Do not reopen completed tickets without recording:

* reason for reopening;
* new evidence;
* affected contracts;
* compatibility impact;
* regression risk;
* tickets that must be re-audited.

11. Every ticket involving:

* seed pools;
* protocol values;
* B4;
* CP2 identity;
* artifact paths;
* manifests;
* policy dispatch;
* metrics;
* CLI execution;
* resume behavior

must be treated as `Scientific-contract-sensitive`.

12. No ticket may change CP2 experimental semantics merely because a refactor opportunity exists.
