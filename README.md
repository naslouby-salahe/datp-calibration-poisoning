# datp-cp

Calibration-channel poisoning of federated threshold personalization in IoT anomaly detection.

This repository studies whether poisoning only benign threshold-calibration scores can shift threshold policies enough to degrade detection or increase alarm burden. Training data, aggregation, model weights, test scores, and test labels remain clean and unchanged throughout.

## Threshold Policies

| Policy | Meaning |
| --- | --- |
| `GLOBAL_THRESHOLD` | Eligible client thresholds are averaged into one shared threshold. |
| `LOCAL_THRESHOLD` | Each eligible client keeps its own calibration-percentile threshold. |
| `CLUSTER_THRESHOLD` | Eligible clients are clustered by calibration-score fingerprints and receive cluster-mean thresholds. |

The primary dataset is N-BaIoT with physical devices as clients. CICIoT2023 is optional diagnostic stretch scope only.

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
data/raw/CIC_IOT_Dataset2023/CSV/
```

N-BaIoT is the confirmatory dataset. CICIoT2023 is diagnostic-only stretch scope.

## Scientific Boundaries

- Poisoning is calibration-channel only.
- Clean calibration arrays must not be mutated in place.
- Reservoirs are victim-local benign calibration scores.
- The injection rule is `REPLACE_FIXED_BUDGET`.
- Seeds use `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])`.
- AUROC must remain invariant because test scores and labels are unchanged.
- Do not claim model poisoning, training poisoning, evasion, privacy, deployment readiness, or broad federated-learning robustness.

The protocol of record is [docs/DATP_CP_Roadmap.md](docs/DATP_CP_Roadmap.md).
