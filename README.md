# datp-cp

Calibration-channel poisoning of federated threshold personalization in IoT anomaly detection.

This repository studies whether poisoning only benign threshold-calibration scores can shift threshold policies enough to degrade detection or alarm burden. Training data, aggregation, model parameters, test scores, and test labels remain clean and unchanged.

## Threshold Policies

The active policies are:

| Policy | Meaning |
| --- | --- |
| `GLOBAL_THRESHOLD` | Eligible client thresholds are averaged into one shared threshold. |
| `LOCAL_THRESHOLD` | Each eligible client keeps its own calibration percentile threshold. |
| `CLUSTER_THRESHOLD` | Eligible clients are clustered by calibration-score fingerprints and receive cluster-mean thresholds. |

The primary dataset is N-BaIoT with physical devices as clients. CICIoT2023 is optional diagnostic stretch scope only.

## Setup

```bash
uv sync --locked --extra test
source .venv/bin/activate
```

If `uv` is unavailable, the fallback is:

```bash
pip install -e ".[test]"
```

## Workflow

Use the canonical Make targets:

```bash
make help
make check
make datp-cp-clean
make datp-cp-smoke
make datp-cp-dry-run
make datp-cp-run
make datp-cp-report
make status
make audit-results
make clean
```

`make check` runs ruff, pyright, and pytest through the repository virtualenv.

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
