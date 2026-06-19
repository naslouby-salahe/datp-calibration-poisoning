from __future__ import annotations

from pathlib import Path

import pytest

from datp.core.enums import Regime
from datp.data.catalog import DatasetID, dataset_spec
from datp.data.paths import (
    data_root,
    prepared_root_for_regime,
    processed_root,
    raw_root,
    regime_c_prepared_dir,
)
from datp.data.regimes.catalog import REGIME_DATASET
from datp.data.splits import (
    Split,
    filename_for_split,
    is_scoring_split,
    iter_scoring_splits,
    split_path,
)


def test_dataset_id_values_are_canonical() -> None:
    assert set(DatasetID) == {
        DatasetID.NBAIOT,
        DatasetID.CICIOT2023,
    }


def test_dataset_specs_exist_once_per_dataset() -> None:
    assert dataset_spec(DatasetID.NBAIOT).feature_count == 115
    assert dataset_spec(DatasetID.CICIOT2023).feature_count == 39


def test_split_filenames_are_canonical() -> None:
    assert filename_for_split(Split.TRAIN) == "train.parquet"
    assert filename_for_split(Split.CAL) == "cal.parquet"
    assert filename_for_split(Split.TEST_BENIGN) == "test_benign.parquet"
    assert filename_for_split(Split.TEST_ATTACK) == "test_attack.parquet"


def test_split_path_builds_correct_path(tmp_path: Path) -> None:
    assert split_path(tmp_path, Split.TRAIN) == tmp_path / "train.parquet"
    assert split_path(tmp_path, Split.CAL) == tmp_path / "cal.parquet"
    assert split_path(tmp_path, Split.TEST_BENIGN) == tmp_path / "test_benign.parquet"
    assert split_path(tmp_path, Split.TEST_ATTACK) == tmp_path / "test_attack.parquet"


def test_iter_scoring_splits_excludes_train() -> None:
    scoring = iter_scoring_splits()
    assert Split.TRAIN not in scoring
    assert Split.CAL in scoring
    assert Split.TEST_BENIGN in scoring
    assert Split.TEST_ATTACK in scoring
    assert len(scoring) == 3


def test_is_scoring_split() -> None:
    assert not is_scoring_split(Split.TRAIN)
    assert is_scoring_split(Split.CAL)
    assert is_scoring_split(Split.TEST_BENIGN)
    assert is_scoring_split(Split.TEST_ATTACK)


def test_regime_dataset_mapping_owned_in_data_layer() -> None:
    assert REGIME_DATASET[Regime.A] == DatasetID.NBAIOT
    assert REGIME_DATASET[Regime.B] == DatasetID.CICIOT2023
    assert REGIME_DATASET[Regime.C] == DatasetID.NBAIOT


def test_prepared_root_uses_canonical_slugs() -> None:
    base = "."
    assert prepared_root_for_regime(Regime.A, base) == processed_root(
        DatasetID.NBAIOT, base
    )
    assert prepared_root_for_regime(Regime.B, base) == processed_root(
        DatasetID.CICIOT2023, base
    )
    # Regime C requires alpha and seed — tested separately


def test_regime_c_prepared_root_requires_alpha_and_seed() -> None:
    with pytest.raises(ValueError):
        prepared_root_for_regime(Regime.C, ".")
    with pytest.raises(ValueError):
        prepared_root_for_regime(Regime.C, ".", alpha=0.5, seed=None)
    with pytest.raises(ValueError):
        prepared_root_for_regime(Regime.C, ".", alpha=None, seed=3)


def test_regime_c_prepared_dir_format(tmp_path: Path) -> None:
    base = processed_root(DatasetID.NBAIOT, tmp_path)
    path = regime_c_prepared_dir(base, alpha=0.5, seed=3)
    assert "regime_c" in str(path)
    assert "seed_3" in str(path)


def test_data_root_returns_data_subdir(tmp_path: Path) -> None:
    assert data_root(".") == Path("data")
    assert data_root(tmp_path) == tmp_path / "data"


def test_raw_root_uses_canonical_raw_slug() -> None:
    assert raw_root(DatasetID.NBAIOT, ".") == Path("data/raw/N-BaIoT")
    assert raw_root(DatasetID.CICIOT2023, ".") == Path(
        "data/raw/CIC_IOT_Dataset2023"
    )


def test_artifacts_dirs_do_not_expose_data_concepts() -> None:
    from datp.artifacts.names import ArtifactDir

    for attr in (
        "DATA",
        "PROCESSED",
        "NBAIOT",
        "CICIOT",
        "REGIME_C",
        "DATA_AUDIT",
    ):
        assert not hasattr(ArtifactDir, attr), (
            f"artifacts.names.ArtifactDir should not export {attr}"
        )


def test_data_splits_does_not_export_artifact_constants() -> None:
    import datp.data.splits as sp

    for attr in (
        "TRAIN_ARTIFACT",
        "CAL_ARTIFACT",
        "TEST_BENIGN_ARTIFACT",
        "TEST_ATTACK_ARTIFACT",
        "SPLIT_ARTIFACT_BY_SPLIT",
    ):
        assert not hasattr(sp, attr), f"data.splits should not export {attr}"


def test_ciciot2023_processed_slug() -> None:
    assert dataset_spec(DatasetID.CICIOT2023).processed_slug == "ciciot2023"


def test_ciciot2023_client_identity_is_merged_file() -> None:
    from datp.data.catalog import ClientIdentity

    assert (
        dataset_spec(DatasetID.CICIOT2023).client_identity == ClientIdentity.MERGED_FILE
    )


def test_regime_b_maps_to_ciciot2023_merged_file() -> None:
    from datp.data.catalog import ClientIdentity

    assert REGIME_DATASET[Regime.B] == DatasetID.CICIOT2023
    spec = dataset_spec(REGIME_DATASET[Regime.B])
    assert spec.client_identity == ClientIdentity.MERGED_FILE


def test_test_attack_labels_artifact_is_data_owned() -> None:
    from datp.data.datasets.ciciot2023.spec import TEST_ATTACK_LABELS_ARTIFACT

    assert TEST_ATTACK_LABELS_ARTIFACT == "test_attack_labels.parquet"
    # Must not be in artifacts.names (data-owned, not pipeline-owned)
    from datp.artifacts.names import ArtifactFile

    assert not hasattr(ArtifactFile, "TEST_ATTACK_LABELS_ARTIFACT")
