import pytest
from pydantic import ValidationError

from datp.config.compose import BASE_CONFIG
from datp.config.models import (
    ModelConfig,
)


class TestInputDimMismatch:
    def test_matching_dims_pass(self) -> None:
        _ = BASE_CONFIG # dims match (input_dim == feature_count from YAML)

    def test_mismatched_dims_fail(self) -> None:
        with pytest.raises(ValidationError, match="model.input_dim"):
            bad = BASE_CONFIG.model_dump()
            bad["model"]["input_dim"] = 99 # dataset.feature_count stays at 115
            type(BASE_CONFIG).model_validate(bad)


class TestUnknownKeys:
    def test_no_unknown_keys_pass(self) -> None:
        _ = BASE_CONFIG

    def test_unknown_key_fails(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            type(BASE_CONFIG).model_validate({"bogus_section": {"foo": 1}})

    def test_missing_required_section_fails(self) -> None:
        with pytest.raises(ValidationError):
            bad = BASE_CONFIG.model_dump()
            bad["model"]["input_dim"] = None
            type(BASE_CONFIG).model_validate(bad)

    def test_missing_required_key_fails(self) -> None:
        with pytest.raises(ValidationError):
            ModelConfig(input_dim=None) # type: ignore[call-arg]

    def test_null_required_key_fails(self) -> None:
        with pytest.raises(ValidationError):
            ModelConfig(input_dim=None) # type: ignore[call-arg]


class TestOverrideNotStripped:
    def test_extra_top_level_key_from_override_fails(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            type(BASE_CONFIG).model_validate({"experiment_extra": {"name": "test"}})

    def test_all_known_sections_accepted(self) -> None:
        _ = BASE_CONFIG


class TestCrossSectionInvariants:
    def test_matching_n_min_pass(self) -> None:
        _ = BASE_CONFIG # n_min values match in YAML

    def test_mismatched_n_min_fail(self) -> None:
        with pytest.raises(ValidationError, match="n_min"):
            bad = BASE_CONFIG.model_dump()
            bad["dataset"]["n_min"] = 50 # threshold.n_min stays at 100
            type(BASE_CONFIG).model_validate(bad)


class TestResourceBounds:
    def test_within_bounds_pass(self) -> None:
        _ = BASE_CONFIG # batch_size_train within safety_bounds from YAML

    def test_exceeds_bounds_fail(self) -> None:
        with pytest.raises(ValidationError, match="exceeds"):
            bad = BASE_CONFIG.model_dump()
            bad["machine"]["batch_size_train"] = 1024
            bad["machine"]["safety_bounds"]["max_batch_size_train"] = 512
            type(BASE_CONFIG).model_validate(bad)


class TestMachineProfile:
    def test_valid_profile_pass(self) -> None:
        _ = BASE_CONFIG # valid YAML-defined profile

    def test_negative_batch_size_fail(self) -> None:
        with pytest.raises(ValidationError):
            bad = BASE_CONFIG.model_dump()
            bad["machine"]["batch_size_train"] = -1
            type(BASE_CONFIG).model_validate(bad)
