from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from datp.data.datasets.nbaiot import (
    DEVICE_DIRS,
    SPLIT_RATIOS,
    prepare_nbaiot,
)
from datp.data.datasets.nbaiot.prepare import _compute_split_indices
from datp.data.splits import Split, filename_for_split

# Buffer-gap keys in SPLIT_RATIOS / _compute_split_indices. Gaps are discarded
# leakage buffers, not Split members, so they are referenced by their dict key.
GAP1_KEY = "gap1"
GAP2_KEY = "gap2"

RAW_DIR = Path("data/raw/N-BaIoT")
N_EXPECTED_DEVICES = 9
N_EXPECTED_FEATURES = 115
_REPRESENTATIVE_DEVICES = ["Danmini_Doorbell", "Ennio_Doorbell"]


_data_available = (
    RAW_DIR.is_dir() and (RAW_DIR / "Danmini_Doorbell" / "benign_traffic.csv").exists()
)
skip_no_data = pytest.mark.skipif(
    not _data_available, reason="Real N-BaIoT data not found"
)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory: pytest.TempPathFactory, monkeypatch_module):
    output_dir = tmp_path_factory.mktemp("nbaiot_integration")

    import datp.data.datasets.nbaiot.prepare as nbaiot_mod

    original_dirs = nbaiot_mod.DEVICE_DIRS
    nbaiot_mod.DEVICE_DIRS = list(_REPRESENTATIVE_DEVICES)
    try:
        result = prepare_nbaiot(
            RAW_DIR, output_dir, n_min=100, seed=42, balanced_test=False
        )
    finally:
        nbaiot_mod.DEVICE_DIRS = original_dirs

    return output_dir, result


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@skip_no_data
@pytest.mark.integration
class TestSplitRatio:
    def test_all_nine_device_dirs_exist(self) -> None:
        assert len(DEVICE_DIRS) == N_EXPECTED_DEVICES
        for device_id in DEVICE_DIRS:
            dev_path = RAW_DIR / device_id
            assert dev_path.is_dir(), f"Missing device directory: {dev_path}"

    def test_all_nine_benign_csv_have_115_features(self) -> None:
        for device_id in DEVICE_DIRS:
            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            assert csv_path.exists(), f"Missing: {csv_path}"
            header = pd.read_csv(csv_path, nrows=0)
            assert len(header.columns) == N_EXPECTED_FEATURES, (
                f"Device {device_id}: expected {N_EXPECTED_FEATURES} cols, "
                f"got {len(header.columns)}"
            )

    def test_split_ratio_on_real_data(self, prepared: tuple[Path, dict]) -> None:
        _, result = prepared
        for device_id in _REPRESENTATIVE_DEVICES:
            info = result[device_id]

            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            n_benign = sum(1 for _ in open(csv_path)) - 1  # minus header

            n_train_expected = math.floor(n_benign * SPLIT_RATIOS[Split.TRAIN])
            n_gap1 = math.floor(n_benign * SPLIT_RATIOS[GAP1_KEY])
            n_cal_expected = math.floor(n_benign * SPLIT_RATIOS[Split.CAL])
            n_gap2 = math.floor(n_benign * SPLIT_RATIOS[GAP2_KEY])
            n_test_expected = (
                n_benign - n_train_expected - n_gap1 - n_cal_expected - n_gap2
            )

            assert info.benign_train_count == n_train_expected, (
                f"{device_id}: train expected {n_train_expected}, got {info.benign_train_count}"
            )
            assert info.benign_cal_count == n_cal_expected, (
                f"{device_id}: cal expected {n_cal_expected}, got {info.benign_cal_count}"
            )
            assert info.test_benign_count == n_test_expected, (
                f"{device_id}: test_benign expected {n_test_expected}, got {info.test_benign_count}"
            )

            total = (
                info.benign_train_count
                + n_gap1
                + info.benign_cal_count
                + n_gap2
                + info.test_benign_count
            )
            assert total == n_benign


@skip_no_data
@pytest.mark.integration
class TestGapContiguous:
    def test_gap_contiguous_on_real_row_counts(self) -> None:
        for device_id in _REPRESENTATIVE_DEVICES:
            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            n_benign = sum(1 for _ in open(csv_path)) - 1

            splits = _compute_split_indices(n_benign)
            train, gap1, cal = splits["train"], splits["gap1"], splits["cal"]
            gap2, test = splits["gap2"], splits["test_benign"]

            assert gap1[0] == train[1], (
                f"{device_id}: gap1 start {gap1[0]} != train end {train[1]}"
            )
            assert cal[0] == gap1[1], (
                f"{device_id}: cal start {cal[0]} != gap1 end {gap1[1]}"
            )
            assert gap2[0] == cal[1], (
                f"{device_id}: gap2 start {gap2[0]} != cal end {cal[1]}"
            )
            assert test[0] == gap2[1], (
                f"{device_id}: test start {test[0]} != gap2 end {gap2[1]}"
            )
            assert test[1] == n_benign

    def test_gaps_are_nonzero(self) -> None:
        for device_id in DEVICE_DIRS:
            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            n_benign = sum(1 for _ in open(csv_path)) - 1

            splits = _compute_split_indices(n_benign)
            gap1_size = splits["gap1"][1] - splits["gap1"][0]
            gap2_size = splits["gap2"][1] - splits["gap2"][0]
            assert gap1_size > 0, f"{device_id}: gap1 is empty (n={n_benign})"
            assert gap2_size > 0, f"{device_id}: gap2 is empty (n={n_benign})"


@skip_no_data
@pytest.mark.integration
class TestNoLeak:
    def test_no_leak_index_level(self) -> None:
        for device_id in DEVICE_DIRS:
            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            n_benign = sum(1 for _ in open(csv_path)) - 1

            splits = _compute_split_indices(n_benign)
            train_range = range(splits["train"][0], splits["train"][1])
            test_range = range(splits["test_benign"][0], splits["test_benign"][1])

            # Ranges are disjoint if max(start) >= min(end)
            assert train_range.stop <= test_range.start, (
                f"{device_id}: train range [{train_range.start}:{train_range.stop}) "
                f"overlaps test range [{test_range.start}:{test_range.stop})"
            )

    def test_no_leak_parquet_content(self, prepared: tuple[Path, dict]) -> None:
        output_dir, result = prepared
        for device_id in _REPRESENTATIVE_DEVICES:
            dev_dir = output_dir / device_id
            train_df = pd.read_parquet(dev_dir / filename_for_split(Split.TRAIN))
            cal_df = pd.read_parquet(dev_dir / filename_for_split(Split.CAL))
            test_df = pd.read_parquet(dev_dir / filename_for_split(Split.TEST_BENIGN))

            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            n_benign = sum(1 for _ in open(csv_path)) - 1
            n_gap1 = math.floor(n_benign * SPLIT_RATIOS[GAP1_KEY])
            n_gap2 = math.floor(n_benign * SPLIT_RATIOS[GAP2_KEY])

            assert (
                len(train_df) + n_gap1 + len(cal_df) + n_gap2 + len(test_df) == n_benign
            ), (
                f"{device_id}: row count mismatch — "
                f"train({len(train_df)}) + gap1({n_gap1}) + cal({len(cal_df)}) + "
                f"gap2({n_gap2}) + test({len(test_df)}) != {n_benign}"
            )


@skip_no_data
@pytest.mark.integration
class TestCalibrationCounts:
    def test_calibration_counts_structural(self) -> None:
        for device_id in DEVICE_DIRS:
            csv_path = RAW_DIR / device_id / "benign_traffic.csv"
            n_benign = sum(1 for _ in open(csv_path)) - 1
            n_cal = math.floor(n_benign * SPLIT_RATIOS[Split.CAL])
            assert n_cal >= 100, (
                f"{device_id}: cal split = {n_cal} rows "
                f"(20% of {n_benign}) — below n_min=100"
            )

    def test_calibration_counts_prepared(self, prepared: tuple[Path, dict]) -> None:
        _, result = prepared
        for device_id in _REPRESENTATIVE_DEVICES:
            info = result[device_id]
            assert info.benign_cal_count >= 100, (
                f"{device_id}: benign_cal_count = {info.benign_cal_count} < 100"
            )
            assert info.calibration_pending is False, (
                f"{device_id}: unexpectedly flagged as Calibration-Pending"
            )

    def test_all_nine_device_dirs_in_constant(self) -> None:
        assert len(DEVICE_DIRS) == N_EXPECTED_DEVICES
        for device_id in DEVICE_DIRS:
            assert (RAW_DIR / device_id).is_dir()
