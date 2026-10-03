# datp-cp

Calibration-channel poisoning of threshold policies (`GLOBAL`, `LOCAL`, `CLUSTER`) on N-BaIoT. Only benign calibration scores are modified.

## Setup

```bash
uv sync --locked --extra test && source .venv/bin/activate
```

Place raw N-BaIoT under `data/raw/N-BaIoT/`.

## Run

```bash
make datp-cp-clean        # datp baseline     train, score, evaluate clean baseline
make datp-cp-dry-run      # datp plan         print experiment grids
make datp-cp-run          # datp poison       bounded poisoning sweep
make datp-cp-sensitivity  # datp sensitivity  sensitivity analyses
make status               # datp status       run completeness
make datp-cp-report       # datp report       audit + tables, figures, summaries -> results/
```

## Develop

```bash
make test    # unit + integration, fails below 90% coverage
make check   # ruff, pyright, Semgrep
make clean   # remove caches
```
