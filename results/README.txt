DATP-CP: Calibration-Channel Poisoning of Federated Threshold Personalization
Curated Release Artifacts — results/
================================================================================

WHAT THIS FOLDER CONTAINS
--------------------------
results/ contains compact, curated artifacts from the DATP-CP N-BaIoT experiments.
These are sufficient to verify, inspect, and reproduce all figures and tables in
the associated paper.

Subfolder overview:

  result_summaries/nbaiot_main/
    Per-cell per-seed metrics.json files (30 files: 3 policies × 10 seeds).
    Contains per-client FPR, TPR, CV metrics, provenance, and schema versions.

  configs/nbaiot_main/
    Fully resolved experiment configurations for each policy/seed cell (30 files).

  split_manifests/nbaiot_main/
    Per-seed scoring manifests recording device splits, model checkpoint identities,
    and scoring code versions (10 files).

  seeds/nbaiot_main/
    Per-seed FL convergence summaries and convergence curves (20 files).

  figure_inputs/
    Figure data JSONs and rendered figures (PNG + PDF):
      figure_1: Per-device FPR comparison (GLOBAL_THRESHOLD vs LOCAL_THRESHOLD)
      figure_2: ECDF of per-client FPR across seeds
      figure_3: Boxplots of CV(FPR) across all three threshold policies and all seeds

  table_inputs/
    Table 3 in CSV and LaTeX format (summary statistics across three policies).

  negative_controls/
    Bootstrap 95% confidence intervals for FPR policy comparisons.
    All reported comparisons exclude zero (statistically significant).

  sanity_checks/
    Metrics schema validation record (status: PASS) and reporting audit record.

  provenance.json
    Code content-hash identities, generation timestamps, split/config identities,
    and the repository HEAD at time of results/ curation.

  script_pointers.json
    Pointers to figure/table generation scripts with expected inputs/outputs.
    Run "make datp-cp-report" to regenerate all figures and tables.

  ARTIFACT_MANIFEST.json
    Machine-readable description of all included and excluded artifacts.

  CHECKSUMS.sha256
    SHA-256 checksums for all files in results/.


WHAT THIS FOLDER DOES NOT CONTAIN
-----------------------------------
- Raw N-BaIoT datasets. Place inputs under data/raw/N-BaIoT/ to reproduce.
- Full outputs/ directory. Only compact curated artifacts are committed here.
- Large intermediate files (raw score parquet files, model checkpoints).
- The full run manifest outputs/conference_calibration_poisoning/nbaiot_main_manifest.json
  (9.3 MB — available in the full outputs/ tree on the research machine).
- Any CICIoT2023, Edge-IIoTset, journal-extension, or stretch diagnostic artifacts.
  These are explicitly outside the release scope of this repository.


SCOPE AND LIMITATIONS
-----------------------
Dataset scope:   N-BaIoT only. Physical IoT devices as FL clients. 9 devices.

Attack type:     Score-level calibration-channel poisoning under REPLACE_FIXED_BUDGET.
                 The attack modifies only benign threshold-calibration scores.
                 Training data, model weights, aggregation, test scores, and test
                 labels remain clean and unchanged throughout.

NOT a proxy for raw-traffic attack:
  The attack operates on already-computed anomaly scores, not on raw network traffic.
  This is a score-level proxy study. No raw-traffic generation is demonstrated.

No deployment claim:
  This is a controlled empirical study. Results are not a deployment assessment.

No privacy guarantee:
  FL topology is used for realism, not as a privacy mechanism.
  No formal privacy guarantee is claimed.

No model/training/aggregation poisoning:
  Only calibration-channel scores are affected. Model weights, gradients,
  aggregation, and training data are untouched.


THRESHOLD POLICIES
------------------
  GLOBAL_THRESHOLD   -- eligible clients share a single averaged threshold
  LOCAL_THRESHOLD    -- each eligible client retains its own calibrated threshold
  CLUSTER_THRESHOLD  -- eligible clients receive cluster-mean thresholds based
                        on calibration-score fingerprints

ATTACK OBJECTIVES
-----------------
  THRESHOLD_RAISE    -- poison to increase false-alarm burden
  THRESHOLD_LOWER    -- poison to degrade detection

SOURCE STRATEGIES
-----------------
  HIGH_SCORE_BENIGN  -- inject high-scoring benign calibration samples
  LOW_SCORE_BENIGN   -- inject low-scoring benign calibration samples
  RANDOM_BENIGN      -- inject randomly sampled benign calibration samples

POISON FRACTIONS (main sweep)
------------------------------
  0, 0.10, 0.20, 0.40


REPRODUCIBILITY
---------------
To reproduce all figures and tables from the included metrics.json files:

  make datp-cp-report

To run the full experiment from scratch (requires N-BaIoT raw data):

  make datp-cp-clean   # prepare N-BaIoT artifacts
  make datp-cp-smoke   # run synthetic smoke invariants
  make datp-cp-run     # run main calibration-poisoning matrix
  make datp-cp-report  # build figures, tables, statistics


CITATION
--------
See CITATION.cff in the repository root.
