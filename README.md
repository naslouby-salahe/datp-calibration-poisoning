# datp-cp

Calibration-channel poisoning of federated threshold personalization in IoT anomaly detection.

This repository studies whether poisoning only benign threshold-calibration scores can shift threshold policies enough to degrade detection or increase alarm burden. Training data, aggregation, model weights, test scores, and test labels remain clean and unchanged throughout.

## Threshold Policies

| Policy | Meaning |
| --- | --- |
| `GLOBAL_THRESHOLD` | Eligible client thresholds are averaged into one shared threshold. |
| `LOCAL_THRESHOLD` | Each eligible client keeps its own calibration-percentile threshold. |
| `CLUSTER_THRESHOLD` | Eligible clients are clustered by calibration-score fingerprints and receive cluster-mean thresholds. |

The dataset is N-BaIoT with physical devices as clients.

## Attack Configuration

| Dimension | Values |
| --- | --- |
| Objectives | `THRESHOLD_RAISE`, `THRESHOLD_LOWER` |
| Sources | `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`, `RANDOM_BENIGN` |
| Injection rule | `REPLACE_FIXED_BUDGET` |
| Poison fractions (main) | 0.0, 0.10, 0.20, 0.40 |

## Setup

```bash
uv sync --locked --extra test
source .venv/bin/activate
```

If `uv` is unavailable:

```bash
pip install -e ".[test]"
```

## Workflow

Run targets in order:

```bash
make check                  # ruff + pyright + full test suite
make datp-cp-unit-tests     # unit tests only (faster dev iteration)

make datp-cp-clean          # [1] generate clean N-BaIoT artifacts
make datp-cp-smoke          # [2] synthetic smoke invariants (must pass)
make datp-cp-dry-run        # [3] enumerate run plan without execution
make datp-cp-run            # [4] run the main calibration-poisoning matrix
make audit-results          # [5] audit completed result artifacts
make datp-cp-report         # [6] build figures, tables, statistics

make status                 # show artifact status at any point
make clean                  # remove caches and temp markers
make help                   # list all targets
```

## Data

Raw datasets are not tracked. Place inputs under:

```text
data/raw/N-BaIoT/
```

Only N-BaIoT is required for the main experiment.

## Scientific Boundaries

- Poisoning is calibration-channel only.
- Clean calibration arrays must not be mutated in place.
- Reservoirs are victim-local benign calibration scores.
- The injection rule is `REPLACE_FIXED_BUDGET`.
- Seeds use `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])`.
- AUROC must remain invariant because test scores and labels are unchanged.
- Do not claim model poisoning, training poisoning, evasion, privacy, deployment readiness, or broad federated-learning robustness.

## Scope and Limitations

**In scope:**
- Score-level calibration-channel poisoning on N-BaIoT with physical IoT devices as FL clients.
- Three threshold policies: `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, `CLUSTER_THRESHOLD`.
- Two attack objectives: `THRESHOLD_RAISE`, `THRESHOLD_LOWER`.
- Three source strategies for the main sweep: `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`, `RANDOM_BENIGN`.
- Empirical measurement of FPR amplification and detection degradation under the `REPLACE_FIXED_BUDGET` injection rule.

**Not in scope:**
- CICIoT2023 is not a supported dataset for this release.
- No raw-traffic generation. The attack operates only on already-computed anomaly scores.
- No deployment claim. This is a controlled empirical study.
- No privacy guarantee. Federated topology is used for FL realism, not as a privacy mechanism.
- No model poisoning, training poisoning, gradient manipulation, or aggregation poisoning.
- No broad FL robustness claim beyond the specific experimental conditions evaluated.

## Citation

If you use this work, please cite it using the metadata in `CITATION.cff`.
