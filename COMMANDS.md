# datp-cp — Command Reference

## 1. Setup

Use the tracked lockfile for reviewer/reproducibility setup:

```bash
uv sync --locked --extra test
source .venv/bin/activate
```

Activate the virtual environment after setup. Run this first in every shell session.

If `uv` is unavailable, `pip install -e ".[test]"` is a convenience-only fallback that installs the declared test extra but does not enforce `uv.lock`.

---

## 2. Static Checks and Tests

```bash
make help
```
List all Makefile targets with descriptions.

```bash
make check
```
Run ruff, pyright, and the full test suite. Use this before any commit.

```bash
make datp-cp-unit-tests
```
Run unit tests only. Faster than `make check` during active development.

---

## 3. datp-cp Workflow

Run targets in the order shown. Each numbered step gates the next.

### [1] Generate clean artifacts

```bash
make datp-cp-clean
```
Generate clean N-BaIoT artifacts (scores, thresholds, manifests) for the calibration-poisoning experiment. Requires raw data under `./data/`.

### [2] Smoke test

```bash
make datp-cp-smoke
```
Run synthetic calibration-poisoning smoke invariants. Validates the full attack pipeline on synthetic data. No real data required. **Must pass before running step [4].**

```bash
make datp-cp-smoke-preview
```
Print the smoke stage config preview. Does not run invariant tests.

### [3] Dry run

```bash
make datp-cp-dry-run
```
Enumerate the N-BaIoT main run plan without execution. Prints the full sweep matrix.

```bash
datp poison dry-run --stage nbaiot_main
```
CLI equivalent.

### [4] Run the calibration-poisoning matrix

```bash
make datp-cp-run
```
Run the authorized N-BaIoT main calibration-poisoning matrix. Reads clean artifacts from `outputs/` and writes poisoned results.

```bash
datp poison run-bounded-sweep --base-dir outputs
```
CLI equivalent.

### [5] Audit results

```bash
make audit-results
```
Audit completed result artifacts and manifest provenance fields. Writes audit artifacts under `outputs/`. Safe to run at any point after step [4] starts.

### [6] Build report artifacts

```bash
make datp-cp-report
```
Build report artifacts (figures, tables, statistics) from completed outputs. Writes to `outputs/`.

---

## 4. Status and Monitoring

```bash
make status
```
Show complete/missing/aborted counts per stage. Safe to run at any point.

---

## 5. Cleanup

```bash
make clean
```
Remove Python caches (`__pycache__/`, `*.pyc`) and temporary run markers (`*.tmp`).

---

## Config Preview

```bash
datp config preview --stage=<S> --policy=<P> --seed=<N>
```
Preview the resolved config for any experiment cell before running it.
