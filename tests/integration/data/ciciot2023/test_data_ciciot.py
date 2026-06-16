from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest

from datp.config.compose import BASE_CONFIG
from datp.data.datasets.ciciot2023 import (
    prepare_ciciot,
    validate_schema,
)
from datp.data.datasets.ciciot2023.spec import (
    BENIGN_LABEL,
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    NUM_CLIENTS,
)
from datp.data.splits import Split, filename_for_split

_ATTACK_RESERVE_FRACTION = BASE_CONFIG.dataset.attack_reserve_fraction


def _prepare_ciciot(
    raw_dir: Path,
    output_dir: Path,
    *,
    cap: int = 50_000,
    n_min: int = 100,
    seed: int = 42,
):
    return prepare_ciciot(
        raw_dir=raw_dir,
        output_dir=output_dir,
        cap=cap,
        n_min=n_min,
        seed=seed,
        attack_reserve_fraction=_ATTACK_RESERVE_FRACTION,
    )


RAW_DIR = Path("data/raw/CIC_IOT_Dataset2023")
MERGED_DIR = RAW_DIR / "CSV" / "MERGED_CSV"
CATEGORY_DIR = RAW_DIR / "CSV" / "CSV"

# Per-category CSV dirs to spot-check (39 feature columns, no Label).
_CATEGORY_SPOT_CHECKS = ["Benign_Final", "DDoS-TCP_Flood", "Recon-PortScan"]

_SINGLE_CLIENT_FILE = "Merged01.csv"

_data_available = (
    MERGED_DIR.is_dir()
    and (MERGED_DIR / "Merged01.csv").exists()
    and (MERGED_DIR / "Merged63.csv").exists()
)
skip_no_data = pytest.mark.skipif(
    not _data_available, reason="Real CICIoT2023 data not found"
)


@skip_no_data
@pytest.mark.integration
class TestSchemaAllFiles:
    """G1-5: 39 feature columns verified across all raw CSV files."""

    def test_schema_all_files_merged_csv_count(self) -> None:
        csv_files = sorted(MERGED_DIR.glob("Merged*.csv"))
        assert len(csv_files) == NUM_CLIENTS, (
            f"Expected {NUM_CLIENTS} MERGED_CSV files, found {len(csv_files)}"
        )

    def test_schema_all_files_merged_40_columns(self) -> None:
        """Every MERGED_CSV file has exactly 40 columns (39 features + Label)."""
        csv_files = sorted(MERGED_DIR.glob("Merged*.csv"))
        assert len(csv_files) == NUM_CLIENTS

        for csv_file in csv_files:
            header = pd.read_csv(csv_file, nrows=0)
            actual_cols = list(header.columns)
            assert len(actual_cols) == 40, (
                f"{csv_file.name}: expected 40 columns, got {len(actual_cols)}"
            )
            assert actual_cols == list(EXPECTED_COLUMNS), (
                f"{csv_file.name}: column names mismatch. "
                f"Missing: {set(EXPECTED_COLUMNS) - set(actual_cols)}. "
                f"Extra: {set(actual_cols) - set(EXPECTED_COLUMNS)}."
            )

    def test_schema_all_files_validate_schema_function(self) -> None:
        validate_schema(RAW_DIR)

    def test_schema_all_files_category_csv_39_columns(self) -> None:
        """Per-category CSV files have 39 feature columns (no Label)."""
        for category in _CATEGORY_SPOT_CHECKS:
            cat_dir = CATEGORY_DIR / category
            if not cat_dir.is_dir():
                pytest.skip(f"Category dir not found: {cat_dir}")

            csv_files = list(cat_dir.glob("*.csv"))
            assert len(csv_files) > 0, f"No CSV files in {cat_dir}"

            csv_file = csv_files[0]
            header = pd.read_csv(csv_file, nrows=0)
            actual_cols = list(header.columns)
            assert len(actual_cols) == 39, (
                f"{category}/{csv_file.name}: expected 39 columns, "
                f"got {len(actual_cols)}"
            )
            assert LABEL_COLUMN not in actual_cols, (
                f"{category}/{csv_file.name}: should not have Label column"
            )
            assert set(actual_cols) == set(FEATURE_COLUMNS), (
                f"{category}/{csv_file.name}: feature columns mismatch. "
                f"Missing: {set(FEATURE_COLUMNS) - set(actual_cols)}. "
                f"Extra: {set(actual_cols) - set(FEATURE_COLUMNS)}."
            )


@skip_no_data
@pytest.mark.integration
class TestCapApplied:
    def test_cap_applied_single_client(self, tmp_path: Path) -> None:
        src = MERGED_DIR / _SINGLE_CLIENT_FILE

        # Load real data, sanitize inf (test focus is cap logic, not data quality).
        df = pd.read_csv(src)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        single_raw = tmp_path / "single_raw" / "CSV" / "MERGED_CSV"
        single_raw.mkdir(parents=True)
        df.to_csv(single_raw / _SINGLE_CLIENT_FILE, index=False)

        output_dir = tmp_path / "out"
        result = _prepare_ciciot(single_raw.parent.parent, output_dir)

        client_id = Path(_SINGLE_CLIENT_FILE).stem # "Merged01"
        info = result[client_id]

        total_output = (
            info.benign_train_count
            + info.benign_cal_count
            + info.test_benign_count
            + info.test_attack_count
        )
        assert total_output <= 50_000, (
            f"Client {client_id}: total output {total_output} exceeds cap 50,000"
        )

        if len(df) > 50_000:
            # May be less than cap if benign rows are fewer than benign budget.
            benign_in_cleaned = (df[LABEL_COLUMN] == BENIGN_LABEL).sum()
            attack_in_cleaned = (df[LABEL_COLUMN] != BENIGN_LABEL).sum()
            attack_budget = min(attack_in_cleaned, 10_000)
            benign_budget = min(benign_in_cleaned, 50_000 - attack_budget)
            expected_total = benign_budget + attack_budget
            assert total_output == expected_total, (
                f"Client {client_id}: expected {expected_total}, got {total_output}"
            )

    def test_cap_applied_priority_preserves_attack(self, tmp_path: Path) -> None:
        src = MERGED_DIR / _SINGLE_CLIENT_FILE

        # Load and sanitize inf (test focus is cap logic, not data quality).
        pdf = pd.read_csv(src, nrows=100_000)
        pdf.replace([np.inf, -np.inf], np.nan, inplace=True)
        pdf.dropna(inplace=True)
        pdf = pdf.reset_index(drop=True)

        if len(pdf) <= 50_000:
            pytest.skip("Client file too small after cleaning to test cap")

        raw_attack_count = (pdf[LABEL_COLUMN] != BENIGN_LABEL).sum()
        raw_benign_count = (pdf[LABEL_COLUMN] == BENIGN_LABEL).sum()

        from datp.data.sampling import apply_ciciot_cap

        df = pl.from_pandas(pdf)
        capped = apply_ciciot_cap(
            df, cap=50_000, label_column=LABEL_COLUMN,
            benign_label=BENIGN_LABEL,
            attack_reserve_fraction=_ATTACK_RESERVE_FRACTION,
            seed=42,
        )
        assert len(capped) <= 50_000

        capped_attack = capped.filter(pl.col(LABEL_COLUMN) != BENIGN_LABEL).height
        capped_benign = capped.filter(pl.col(LABEL_COLUMN) == BENIGN_LABEL).height

        # Attack budget is min(raw_attack, cap * attack_reserve = 10,000).
        expected_attack_budget = min(raw_attack_count, 10_000)
        assert capped_attack == expected_attack_budget, (
            f"Expected {expected_attack_budget} attack rows in capped output, "
            f"got {capped_attack}"
        )

        expected_benign = min(raw_benign_count, 50_000 - expected_attack_budget)
        assert capped_benign == expected_benign, (
            f"Expected {expected_benign} benign rows, got {capped_benign}"
        )

    def test_cap_applied_artifacts_are_parquet(self, tmp_path: Path) -> None:
        src = MERGED_DIR / _SINGLE_CLIENT_FILE

        # Load and sanitize (test focus is artifact format, not data quality).
        df = pd.read_csv(src, nrows=60_000)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        single_raw = tmp_path / "single_raw" / "CSV" / "MERGED_CSV"
        single_raw.mkdir(parents=True)
        df.to_csv(single_raw / _SINGLE_CLIENT_FILE, index=False)

        output_dir = tmp_path / "out"
        _prepare_ciciot(single_raw.parent.parent, output_dir)

        client_id = Path(_SINGLE_CLIENT_FILE).stem
        client_out = output_dir / "ciciot2023" / client_id

        for artifact in [
            filename_for_split(Split.TRAIN),
            filename_for_split(Split.CAL),
            filename_for_split(Split.TEST_BENIGN),
            filename_for_split(Split.TEST_ATTACK),
        ]:
            path = client_out / artifact
            assert path.exists(), f"Missing artifact: {path}"
            artifact_df = pd.read_parquet(path)
            assert isinstance(artifact_df, pd.DataFrame)


@skip_no_data
@pytest.mark.integration
class TestEvalIncompleteFlag:
    def test_eval_incomplete_flag_synthetic_in_real_structure(
        self, tmp_path: Path
    ) -> None:
        src = MERGED_DIR / _SINGLE_CLIENT_FILE
        df = pd.read_csv(src, nrows=5000)
        benign_only = df[df[LABEL_COLUMN] == BENIGN_LABEL].head(1000)

        if len(benign_only) == 0:
            pytest.skip("No benign rows found in sample for test construction")

        single_raw = tmp_path / "raw" / "CSV" / "MERGED_CSV"
        single_raw.mkdir(parents=True)
        benign_only.to_csv(single_raw / "Merged01.csv", index=False)

        output_dir = tmp_path / "out"
        result = _prepare_ciciot(single_raw.parent.parent, output_dir)

        assert result["Merged01"].evaluation_incomplete is True

    def test_eval_incomplete_flag_real_client_has_attacks(self) -> None:
        df = pd.read_csv(MERGED_DIR / _SINGLE_CLIENT_FILE, nrows=10_000)
        attack_count = (df[LABEL_COLUMN] != BENIGN_LABEL).sum()
        assert attack_count > 0, (
            "Expected at least some attack records in Merged01.csv sample"
        )


@skip_no_data
@pytest.mark.integration
class TestCalibrationPendingFlag:
    def test_calibration_pending_flag_few_benign(self, tmp_path: Path) -> None:
        """A client with very few benign records is flagged calibration-pending.

        Calibration-Pending check: floor(total_benign_pre_cap * 0.15) < n_min.
        With 50 benign rows: floor(50 * 0.15) = 7 < 100 → pending.
        """
        src = MERGED_DIR / _SINGLE_CLIENT_FILE
        df = pd.read_csv(src, nrows=10_000)

        benign_rows = df[df[LABEL_COLUMN] == BENIGN_LABEL].head(50)
        attack_rows = df[df[LABEL_COLUMN] != BENIGN_LABEL].head(200)

        if len(benign_rows) < 50 or len(attack_rows) == 0:
            pytest.skip("Insufficient rows in sample for test construction")

        client_df = pd.concat([benign_rows, attack_rows], ignore_index=True)

        single_raw = tmp_path / "raw" / "CSV" / "MERGED_CSV"
        single_raw.mkdir(parents=True)
        client_df.to_csv(single_raw / "Merged01.csv", index=False)

        output_dir = tmp_path / "out"
        result = _prepare_ciciot(single_raw.parent.parent, output_dir)

        assert result["Merged01"].calibration_pending is True

    def test_calibration_pending_flag_enough_benign(self, tmp_path: Path) -> None:
        """A client with enough benign is NOT calibration-pending.

        With 2000 benign rows: floor(2000 * 0.15) = 300 >= 100 → eligible.
        """
        src = MERGED_DIR / _SINGLE_CLIENT_FILE
        df = pd.read_csv(src)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        benign_rows = df[df[LABEL_COLUMN] == BENIGN_LABEL].head(2000)
        attack_rows = df[df[LABEL_COLUMN] != BENIGN_LABEL].head(500)

        if len(benign_rows) < 2000:
            pytest.skip("Not enough benign rows in sample")

        client_df = pd.concat([benign_rows, attack_rows], ignore_index=True)

        single_raw = tmp_path / "raw" / "CSV" / "MERGED_CSV"
        single_raw.mkdir(parents=True)
        client_df.to_csv(single_raw / "Merged01.csv", index=False)

        output_dir = tmp_path / "out"
        result = _prepare_ciciot(single_raw.parent.parent, output_dir)

        assert result["Merged01"].calibration_pending is False

    def test_calibration_pending_flag_real_full_client(self, tmp_path: Path) -> None:
        src = MERGED_DIR / _SINGLE_CLIENT_FILE

        # Load and sanitize (test focus is flag logic, not data quality).
        df = pd.read_csv(src)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        single_raw = tmp_path / "raw" / "CSV" / "MERGED_CSV"
        single_raw.mkdir(parents=True)
        df.to_csv(single_raw / _SINGLE_CLIENT_FILE, index=False)

        output_dir = tmp_path / "out"
        result = _prepare_ciciot(single_raw.parent.parent, output_dir)

        client_id = Path(_SINGLE_CLIENT_FILE).stem
        info = result[client_id]

        assert info.total_benign_pre_cap is not None
        cal_estimate = math.floor(info.total_benign_pre_cap * 0.15)
        expected_pending = cal_estimate < 100
        assert info.calibration_pending is expected_pending, (
            f"Client {client_id}: total_benign_pre_cap={info.total_benign_pre_cap}, "
            f"cal_estimate={cal_estimate}, expected pending={expected_pending}, "
            f"got {info.calibration_pending}"
        )
