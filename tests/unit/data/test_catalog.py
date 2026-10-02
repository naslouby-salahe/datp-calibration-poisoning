"""Unit tests for dataset catalog enumeration and metadata."""

from __future__ import annotations

import pytest

from datp.data.catalog import (
    DatasetID,
    DatasetSpec,
    SplitPolicy,
    SplitPolicyRole,
    dataset_display_name,
    dataset_processed_slug,
    dataset_spec,
)
from datp.core.enums import (
    ArtifactFile,
    NBaIoTAttackFamily,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
)
from datp.data.datasets.nbaiot.spec import (
    ATTACK_FAMILY_DIRS,
    DEVICE_DIRS,
    DEVICE_FAMILY_MAP,
)
from datp.reporting.constants import NBAIOT_DEVICE_SHORT_LABELS


class TestDatasetID:
    """DatasetID enum values."""

    def test_all_members_present(self) -> None:
        assert set(DatasetID) == {
            DatasetID.NBAIOT,
        }

    def test_values_are_lowercase_slugs(self) -> None:
        for member in DatasetID:
            assert member.value == member.value.lower()
            assert " " not in member.value


class TestNBaIoTEnums:
    def test_device_catalog_and_family_map_cover_the_enum_domain(self) -> None:
        assert set(DEVICE_DIRS) == set(NBaIoTDevice)
        assert set(DEVICE_FAMILY_MAP) == set(NBaIoTDevice)
        assert set(DEVICE_FAMILY_MAP.values()) == set(NBaIoTDeviceFamily)

    def test_attack_families_and_report_labels_cover_their_enum_domains(self) -> None:
        assert set(ATTACK_FAMILY_DIRS) == set(NBaIoTAttackFamily)
        assert set(NBAIOT_DEVICE_SHORT_LABELS) == set(NBaIoTDevice)
        assert ArtifactFile.BENIGN_TRAFFIC.value == "benign_traffic.csv"


class TestDatasetPolicyEnums:

    def test_split_policy_role_members(self) -> None:
        assert set(SplitPolicyRole) == {
            SplitPolicyRole.TRAIN,
            SplitPolicyRole.GAP1,
            SplitPolicyRole.CAL,
            SplitPolicyRole.GAP2,
            SplitPolicyRole.TEST_BENIGN,
        }

class TestSplitPolicy:
    """Split-policy ratio configuration."""

    def test_construction(self) -> None:
        sp = SplitPolicy(
            ratios={SplitPolicyRole.TRAIN: 0.6, SplitPolicyRole.CAL: 0.2},
        )
        assert sp.ratios == {SplitPolicyRole.TRAIN: 0.6, SplitPolicyRole.CAL: 0.2}

    def test_frozen(self) -> None:
        sp = SplitPolicy(ratios={})
        with pytest.raises(Exception):
            setattr(sp, "ratios", {})


def _make_spec(feature_count: int = 10) -> DatasetSpec:
    return DatasetSpec(
        id=DatasetID.NBAIOT,
        display_name="Test",
        processed_slug="test",
        feature_count=feature_count,
        feature_columns=None,
        label_column=None,
        benign_label=None,
        raw_root_slug="test_raw",
        split_policy=SplitPolicy(
            ratios={SplitPolicyRole.TRAIN: 0.7, SplitPolicyRole.CAL: 0.3}
        ),
        family_map=None,
        device_ids=(),
        attack_family_dirs=(),
        expected_client_count=None,
    )


class TestDatasetSpec:
    """DatasetSpec field validation."""

    def test_minimal_construction(self) -> None:
        spec = _make_spec()
        assert spec.id == DatasetID.NBAIOT
        assert spec.feature_count == 10

    def test_frozen(self) -> None:
        spec = _make_spec()
        with pytest.raises(Exception):
            setattr(spec, "feature_count", 99)


class TestDatasetSpecHelper:
    """DatasetSpec helper lookups."""

    def test_returns_correct_spec(self) -> None:
        spec = dataset_spec(DatasetID.NBAIOT)
        assert spec.id == DatasetID.NBAIOT
        assert spec.display_name == "N-BaIoT"

    def test_nbaiot_properties(self) -> None:
        spec = dataset_spec(DatasetID.NBAIOT)
        assert spec.feature_count == 115
        assert spec.split_policy.ratios[SplitPolicyRole.CAL] == 0.20
        assert spec.family_map is not None

    def test_raises_keyerror_for_invalid_id(self) -> None:
        with pytest.raises(KeyError):
            dataset_spec("not_an_enum")


class TestDatasetDisplayName:
    """Dataset display name generation."""

    def test_nbaiot(self) -> None:
        assert dataset_display_name(DatasetID.NBAIOT) == "N-BaIoT"


class TestDatasetProcessedSlug:
    """Processed data directory slug generation."""

    def test_nbaiot(self) -> None:
        assert dataset_processed_slug(DatasetID.NBAIOT) == "nbaiot"
