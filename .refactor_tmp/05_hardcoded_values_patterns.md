# 05 — Hardcoded Values, Raw Strings, and Repeated Pattern Inventory

## A. Scientific Values and Protocol Defaults

### `0.10`

- Category: `numeric value`
- Occurrences:
  - `src/datp/artifacts/poison_names.py` - `TAIL_MASS = 0.10`
  - `src/datp/core/poison_enums.py` - `BOUNDED_SWEEP_FRACTIONS` includes `0.10`
  - `src/datp/core/poison_enums.py` - `FULL_SWEEP_FRACTIONS` includes `0.10`
  - `src/datp/conf/config.yaml` - dataset split fractions
- Related constants: `TAIL_MASS`, `BOUNDED_SWEEP_FRACTIONS`, `FULL_SWEEP_FRACTIONS`

### `0.05`

- Category: `numeric value`
- Occurrences:
  - `src/datp/core/poison_enums.py` - `FULL_SWEEP_FRACTIONS` includes `0.05`
  - `src/datp/artifacts/poison_names.py` - `TRIM_FRACTION_PRIMARY = 0.05`
  - `src/datp/conf/config.yaml` - quality_gates dispersion thresholds
- Related constants: `FULL_SWEEP_FRACTIONS`, `TRIM_FRACTION_PRIMARY`

### `0.95` / `95`

- Category: `numeric value`
- Occurrences:
  - `src/datp/artifacts/poison_names.py` - `THRESHOLD_QUANTILE = 0.95`
  - `src/datp/conf/config.yaml` - threshold.q: 0.95
  - `src/datp/conf/config.yaml` - statistics.ci_level: 0.95
- Related constants: `THRESHOLD_QUANTILE`
- Related configuration fields: `ThresholdConfig.q`, `StatisticsConfig.ci_level`

### `100`

- Category: `numeric value`
- Occurrences:
  - `src/datp/artifacts/poison_names.py` - `N_MIN = 100`
  - `src/datp/conf/config.yaml` - dataset.n_min: 100
  - `src/datp/conf/config.yaml` - threshold.n_min: 100
- Related constants: `N_MIN`

### `3` (B4 K)

- Category: `numeric value`
- Occurrences:
  - `src/datp/artifacts/poison_names.py` - `B4_K = 3`
  - `src/datp/conf/config.yaml` - `threshold.b4_k_regime_a: 3`
- Related constants: `B4_K`

### `0.0` (zero fraction)

- Category: `numeric value`
- Occurrences:
  - `src/datp/core/poison_enums.py` - `BOUNDED_SWEEP_FRACTIONS` includes `0.0`
  - `src/datp/core/poison_enums.py` - `FULL_SWEEP_FRACTIONS` includes `0.0`
- Contexts: clean (unpoisoned) control cell

### `0.40` (max fraction)

- Category: `numeric value`
- Occurrences:
  - `src/datp/core/poison_enums.py` - both `BOUNDED_SWEEP_FRACTIONS` and `FULL_SWEEP_FRACTIONS` include `0.40`

### Seed values

- `0, 1, 2, 3, 4` — `TRAINING_SEEDS` in `poison_names.py` and `config.yaml`
- `100, 101, 102, 103, 104` — `POISONING_SEEDS` in `poison_names.py`
- `300, 301, 302, 303, 304` — `ANALYSIS_SEEDS` in `poison_names.py`
- `400` — `COMPROMISE_PATTERN_SEED` in `poison_names.py`
- `42` — `B4_RANDOM_STATE` in `poison_names.py`, `bootstrap_seed` in `config.yaml`

## B. Raw Domain Strings

### `"B2_PERSONALIZED"`

- Category: `raw domain string`
- Related enums: `ThresholdPolicy.B2_PERSONALIZED`
- Contexts: manifest serialization, CLI parsing, test expectations

### `"b1_global"`, `"b2_personalized"`, `"b4_cluster"`

- Category: `raw domain string`
- Related enums: `ThresholdPolicy`
- Contexts: manifest values, path segments, CLI

### `"nbaiot"`, `"ciciot2023"`

- Category: `raw domain string`
- Related enums: `DatasetID`
- Contexts: dataset identifiers in config, paths

### `"a"`, `"b"`, `"c"`

- Category: `raw domain string`
- Related enums: `Regime`
- Contexts: regime identifiers in paths, config

### `"b0"`, `"b1"`, `"b2"`, `"b3"`, `"b4"`

- Category: `raw domain string`
- Related enums: `Baseline`
- Contexts: baseline identifiers in paths, config, results

### `"seed_"`, `"round_"`, `"alpha_"`

- Category: `raw domain string`
- Related enums: `PathToken`
- Contexts: path construction in `layout.py`, `identity.py`

### `"reconstruction_error"`

- Category: `raw domain string`
- Occurrences: `src/datp/scoring/schema.py` - `SCORE_COLUMN`
- Contexts: Parquet score file column name

### `"threshold_raise"`, `"threshold_lower"`

- Category: `raw domain string`
- Related enums: `AttackerObjective`
- Contexts: manifest serialization

### `"single_client"`, `"multi_client"`, `"all_clients_diagnostic_only"`

- Category: `raw domain string`
- Related enums: `PoisoningTargetScope`
- Contexts: manifest serialization

### `"conference_calibration_poisoning"`

- Category: `raw domain string`
- Occurrences: `src/datp/artifacts/poison_names.py` - `CALIBRATION_POISONING_OUTPUT_ROOT`
- Contexts: output root directory name

## C. Repeated Numeric Values

### `0.10`

- See section A above (tail mass, fraction grid, trim appendix)

### `0.05`

- See section A above (full grid, trim primary)

### `0.0`

- See section A above (zero fraction control)

### `0.40`

- See section A above (max fraction)

## D. Paths, Artifact Names, Manifest Keys, and Schema Keys

### `outputs/`

- Category: `path prefix`
- Occurrences: `ArtifactLayout.base_dir`, `PoisonLayout.base_dir`, various CLI commands

### `conference_calibration_poisoning`

- Category: `output-root path fragment`
- Constant: `CALIBRATION_POISONING_OUTPUT_ROOT` in `datp/artifacts/poison_names.py`
- Related layout symbols: `PoisonLayout.poison_output_root`

### `model.pt`

- Category: `artifact name`
- Enum member: `ArtifactFile.MODEL_CHECKPOINT` in `datp/core/enums.py`

### `metrics.json`

- Category: `artifact name`
- Enum member: `ArtifactFile.METRICS` in `datp/core/enums.py`

### `DONE.txt`, `IN_PROGRESS`, `ABORTED.txt`

- Category: `artifact name`
- Enum members: `ArtifactFile` in `datp/core/enums.py` and `RunFile` in `datp/artifacts/poison_names.py`

### Manifest keys in `PayloadKey` (metric_enums.py)

- Keys: `client_id`, `per_client`, `confusion_matrix`, `baseline`, `regime`, `seed`, `alpha`, `coverage_ratio`, `dataset`, `eligible_count`, `pending_count`, `threshold_value`, etc.
- Contexts: JSON serialization of metrics, evaluation results

### Bounded sweep manifest keys

- Keys: `policy`, `source`, `objective`, `fraction`, `target_scope`, `victim_id`, `training_seed`, `poisoning_seed`, `seed_record`, `delta_tau`, `cv_fpr`, `mean_fpr`, `coverage_ratio`, `mu_flag_triggered`, `auroc_invariant`, `blast_fraction`, etc.
- Defined in: `BoundedSweepResultRow` in `bounded_sweep_manifest.py`

## E. Repeated Parameter Groups

### Calibration-poisoning cell identity

- Fields observed across 5+ locations: `policy`, `source`, `objective`, `fraction`, `target_scope`, `victim_id`, `training_seed`, `poisoning_seed`
- Existing typed containers: `SweepCellSpec`, `CellId`, `SeedRecord` (partial overlap)
- See `03_methods_inputs_outputs.md` section G for full details.

### B4 clustering parameters

- Fields observed across 4+ locations: `k`, `n_init`, `max_iter`, `random_state`
- Existing typed containers: `B4ClusterConfig` in `datp/config/attack_config.py`
- See `04_enums_dataclasses_constants.md` section D for full details.

## F. Repeated Configuration and Dispatch Patterns

### Config validation patterns

- `if not (0.0 <= self.fraction <= 1.0)` in `CellId.__post_init__`
- Fraction-in-grid validation in `guardrails.assert_fractions_in_locked_grid`
- Policy-not-B3 validation in `guardrails.assert_policy_not_b3`

### Path construction patterns

- `_seed_segment(seed, alpha)` in `artifacts/layout.py` — repeated for checkpoint, score, result roots
- `_fraction_segment`, `_scope_segment`, `_training_seed_segment`, `_poisoning_seed_segment` in `poison_layout.py`

## G. Local Literals

(Notable string/numeric literals found in implementation modules that are not derived from constants or config.)

### `"f_{fraction:.2f}"`

- Location: `src/datp/artifacts/poison_layout.py` - `_fraction_segment`
- Context: fraction-to-path-segment conversion

### `"scope_{scope.value}"`

- Location: `src/datp/artifacts/poison_layout.py` - `_scope_segment`

### `"train_{seed}"`, `"poison_{seed}"`

- Location: `src/datp/artifacts/poison_layout.py` - training and poisoning seed segment builders

### `"reconstruction_error"`

- Location: `src/datp/scoring/schema.py`
- Context: score Parquet column name
