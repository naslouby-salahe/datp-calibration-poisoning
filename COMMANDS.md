# DATP — Command Reference

## 1. Setup

Use the tracked lockfile for reviewer/reproducibility setup:

```bash
uv sync --locked --extra test
```

```bash
source .venv/bin/activate
```
Activate the virtual environment after setup. Run this first in every shell session.

If `uv` is unavailable, `pip install -e ".[test]"` is a convenience-only fallback that installs the declared test extra but does not enforce `uv.lock`.

---

## 2. Environment checks

```bash
make help
```
List all Makefile targets.

```bash
make check
```
Run ruff, pyright, and the full test suite. Use this before any commit.

```bash
datp config preview --stage=<S> --policy=<P> --seed=<N>
```
Preview resolved config for any experiment cell.

---

## 3. datp-cp Workflow

### 3.1 Generate clean artifacts

```bash
make datp-cp-clean
```
Generate clean N-BaIoT artifacts (scores, checkpoints, manifests) for the calibration-poisoning experiment. Requires raw data under `./data/`.

### 3.2 Smoke test

```bash
make datp-cp-smoke
```
Run synthetic calibration-poisoning smoke diagnostics. Validates the full attack pipeline on synthetic data. No real data required.

### 3.3 Dry run

```bash
make datp-cp-dry-run
```
Enumerate the N-BaIoT main run plan without execution. Prints the full sweep matrix.

```bash
datp poison dry-run --stage nbaiot_main
```
CLI equivalent.

### 3.4 Run the calibration-poisoning matrix

```bash
make datp-cp-run
```
Run the authorized N-BaIoT main calibration-poisoning matrix. Reads clean artifacts from `outputs/` and writes poisoned results.

```bash
datp poison run-bounded-sweep --base-dir outputs
```
CLI equivalent.

### 3.5 Build report artifacts

```bash
make datp-cp-report
```
Build datp-cp report artifacts from completed outputs. Writes figures, tables, and statistics to `outputs/`.

---

## 4. Audit / Status

```bash
make status
```
Show complete/missing/aborted counts per stage. < 1 min.

```bash
make audit-results
```
Audit completed result artifacts; write all audit artifacts under `artifacts/audit/`. < 1 min.

---

## 5. Cleanup

```bash
make clean
```
Remove Python caches (`__pycache__/`, `*.pyc`) and temporary run markers (`*.tmp`).
