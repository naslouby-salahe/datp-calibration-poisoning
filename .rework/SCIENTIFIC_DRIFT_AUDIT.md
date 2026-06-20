# Scientific Drift Audit — datp-cp

Audit of the codebase for violations of the calibration-channel-only scientific boundary.

---

## Verdict

Not yet audited.

---

## Hard Boundary (must never be crossed)

    Attack surface: benign calibration scores ONLY
    Never alter: training data, training labels, model weights, gradients,
                 FedAvg aggregation, server code, test scores, test labels, test data,
                 other clients' raw data

---

## Drift Search Results

Run this search to find potential violations:

    grep -RIn \
      --exclude-dir=.git --exclude-dir=.venv --exclude-dir=outputs --exclude-dir=.rework \
      -iE "model.?poison|weight.?poison|gradient.?poison|train.?poison|aggregat.?poison|evasion|backdoor|privacy|deployment|latency|edge.iiot" .

Also search for clean-array mutation:

    grep -RIn --include="*.py" -E "\[:\]\s*=|\[:, :\]\s*=" src/datp/

Also search for integer seed addition:

    grep -RIn --include="*.py" -E "seed\s*\+\s*|seed\s*\+=|training_seed\s*\+" src/datp/

Also search for cross-test-score reservoir:

    grep -RIn --include="*.py" -E "test.*reservoir|reservoir.*test" src/datp/

---

## Findings

### Status: not yet audited

Write findings here and create CLAUDE tasks for all CRITICAL findings.

### Finding Template

    ### SD-NNN — <description>
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    File: <path>
    Line: <line>
    Evidence: <the offending code>
    Risk: <scientific impact>
    Required fix: <what must change>
    Status: TODO
