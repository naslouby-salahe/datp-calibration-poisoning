# Project Structure Audit — datp-cp

Audit of the repository package structure and module ownership.

---

## Verdict

Not yet audited.

---

## Expected Structure

    src/datp/
      __init__.py
      app/
        cli/
          __init__.py
          __main__.py
          <datp-cp subcommands>
      calibration/
        <calibration-channel poisoning logic>
      config/
        <dataclass configs>
      constants/
        <named constants>
      data/
        <dataset loading and preprocessing>
      evaluation/
        <metrics: CV(FPR), AUROC, coverage_ratio, etc.>
      federated/
        <FL training pipeline>
      models/
        <autoencoder architecture>
      pipeline/
        <orchestration pipeline>
      reporting/
        <report generation>
      statistics/
        <bootstrap CI, seed aggregation>
      thresholding/
        <threshold computation per policy>
      artifacts/
        <artifact path builders and manifest writers>

---

## Module Ownership Rules

    calibration/ owns: poisoning logic, injection rule, reservoir sampling
    thresholding/ owns: GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD computation
    evaluation/ owns: metrics, paired comparison
    statistics/ owns: seed aggregation, bootstrap CI
    artifacts/ owns: output paths, manifest writing, DONE markers
    config/ owns: frozen dataclasses for all configs
    constants/ owns: all named scientific constants

No module should duplicate ownership of another module's domain.

---

## Findings

### Status: not yet audited

Agents: inspect src/datp/ and map actual package structure.

    find src/datp -name "*.py" | sort | head -60

Write the actual structure here and flag mismatches with the expected structure.
