"""Tests for datp.data.catalog — enums, dataclasses, and registry functions."""

from __future__ import annotations

import pytest

from datp.data.catalog import (
    CapPolicy,
    CapStrategy,
    ClientIdentity,
    DatasetID,
    DatasetSpec,
    RawLayout,
    SplitPolicy,
    SplitPolicyKind,
    SplitPolicyRole,
    dataset_display_name,
    dataset_processed_slug,
    dataset_spec,
)


class TestDatasetID:
    def test_all_members_present(self) -> None:
        assert set(DatasetID) == {
            DatasetID.NBAIOT,
            DatasetID.CICIOT2023,
        }

    def test_values_are_lowercase_slugs(self) -> None:
        for member in DatasetID:
            assert member.value == member.value.lower()
            assert " " not in member.value


class TestClientIdentity:
    def test_expected_members_present(self) -> None:
        assert ClientIdentity.DEVICE_DIRECTORY in ClientIdentity
        assert ClientIdentity.MERGED_FILE in ClientIdentity

    def test_values_are_snake_case(self) -> None:
        for member in ClientIdentity:
            assert "_" in member.value or member.value.islower()


class TestDatasetPolicyEnums:
    def test_split_policy_kind_members(self) -> None:
        assert set(SplitPolicyKind) == {
            SplitPolicyKind.CHRONOLOGICAL_GAPPED,
            SplitPolicyKind.STRATIFIED_RANDOM,
        }

    def test_split_policy_role_members(self) -> None:
        assert set(SplitPolicyRole) == {
            SplitPolicyRole.TRAIN,
            SplitPolicyRole.GAP1,
            SplitPolicyRole.CAL,
            SplitPolicyRole.GAP2,
            SplitPolicyRole.TEST_BENIGN,
        }

    def test_cap_strategy_members(self) -> None:
        assert set(CapStrategy) == {CapStrategy.ATTACK_PRESERVING}


class TestSplitPolicy:
    def test_construction(self) -> None:
        sp = SplitPolicy(
            name=SplitPolicyKind.CHRONOLOGICAL_GAPPED,
            calibration_benign_only=True,
            chronological=True,
            contiguous_gaps=False,
            ratios={SplitPolicyRole.TRAIN: 0.6, SplitPolicyRole.CAL: 0.2},
        )
        assert sp.name == SplitPolicyKind.CHRONOLOGICAL_GAPPED
        assert sp.calibration_benign_only is True
        assert sp.chronological is True
        assert sp.contiguous_gaps is False
        assert sp.ratios == {SplitPolicyRole.TRAIN: 0.6, SplitPolicyRole.CAL: 0.2}

    def test_frozen(self) -> None:
        sp = SplitPolicy(
            name=SplitPolicyKind.STRATIFIED_RANDOM,
            calibration_benign_only=False,
            chronological=False,
            contiguous_gaps=False,
            ratios={},
        )
        with pytest.raises(Exception):
            sp.name = "other"  # type: ignore[misc]


class TestCapPolicy:
    def test_construction(self) -> None:
        cp = CapPolicy(
            total=50000,
            attack_reserve=10000,
            strategy=CapStrategy.ATTACK_PRESERVING,
        )
        assert cp.total == 50000
        assert cp.attack_reserve == 10000
        assert cp.strategy == CapStrategy.ATTACK_PRESERVING

    def test_frozen(self) -> None:
        cp = CapPolicy(
            total=100,
            attack_reserve=10,
            strategy=CapStrategy.ATTACK_PRESERVING,
        )
        with pytest.raises(Exception):
            cp.total = 200  # type: ignore[misc]


def _make_spec(feature_count: int = 10) -> DatasetSpec:
    return DatasetSpec(
        id=DatasetID.NBAIOT,
        display_name="Test",
        processed_slug="test",
        feature_count=feature_count,
        feature_columns=None,
        label_column=None,
        benign_label=None,
        client_identity=ClientIdentity.DEVICE_DIRECTORY,
        raw_layout=RawLayout(root_slug="test_raw"),
        split_policy=SplitPolicy(
            name=SplitPolicyKind.STRATIFIED_RANDOM,
            calibration_benign_only=True,
            chronological=False,
            contiguous_gaps=False,
            ratios={SplitPolicyRole.TRAIN: 0.7, SplitPolicyRole.CAL: 0.3},
        ),
        cap_policy=None,
        family_map=None,
        device_ids=(),
        attack_family_dirs=(),
        expected_client_count=None,
    )


class TestDatasetSpec:
    def test_minimal_construction(self) -> None:
        spec = _make_spec()
        assert spec.id == DatasetID.NBAIOT
        assert spec.feature_count == 10
        assert spec.cap_policy is None

    def test_frozen(self) -> None:
        spec = _make_spec()
        with pytest.raises(Exception):
            spec.feature_count = 99  # type: ignore[misc]


class TestDatasetSpecHelper:
    def test_returns_correct_spec(self) -> None:
        spec = dataset_spec(DatasetID.NBAIOT)
        assert spec.id == DatasetID.NBAIOT
        assert spec.display_name == "N-BaIoT"

    def test_nbaiot_properties(self) -> None:
        spec = dataset_spec(DatasetID.NBAIOT)
        assert spec.feature_count == 115
        assert spec.client_identity == ClientIdentity.DEVICE_DIRECTORY
        assert spec.cap_policy is None
        assert spec.family_map is not None

    def test_ciciot2023_properties(self) -> None:
        spec = dataset_spec(DatasetID.CICIOT2023)
        assert spec.feature_count == 39
        assert spec.client_identity == ClientIdentity.MERGED_FILE
        assert spec.cap_policy is not None

    def test_raises_keyerror_for_invalid_id(self) -> None:
        with pytest.raises(KeyError):
            dataset_spec("not_an_enum")  # type: ignore[arg-type]


class TestDatasetDisplayName:
    def test_nbaiot(self) -> None:
        assert dataset_display_name(DatasetID.NBAIOT) == "N-BaIoT"

    def test_ciciot2023(self) -> None:
        assert dataset_display_name(DatasetID.CICIOT2023) == "CICIoT2023"


class TestDatasetProcessedSlug:
    def test_nbaiot(self) -> None:
        assert dataset_processed_slug(DatasetID.NBAIOT) == "nbaiot"

    def test_ciciot2023(self) -> None:
        assert dataset_processed_slug(DatasetID.CICIOT2023) == "ciciot2023"
