from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import datp.data.regimes.regime_c as regime_c_mod
from datp.config.compose import BASE_CONFIG
from datp.core.identity import format_alpha_dir
from datp.data.datasets.nbaiot import DEVICE_DIRS
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.data.regimes.regime_c import partition_regime_c
from datp.data.splits import Split, filename_for_split

ALPHA_LEVELS: list[float] = [0.1, 0.3, 0.5, 1.0, 10.0, math.inf]
N_CLIENTS = 20
N_FEATURES = 10
SEED = 42
TRAIN_FRAC = BASE_CONFIG.dataset.regime_c_train_fraction
CAL_FRAC = BASE_CONFIG.dataset.regime_c_cal_fraction


def _create_synthetic_nbaiot_raw(
    raw_dir: Path,
    n_features: int = N_FEATURES,
    n_benign: int = 300,
    n_attack: int = 80,
) -> None:
    rng = np.random.default_rng(99)
    cols = [f"feat_{i}" for i in range(n_features)]

    for device_id in DEVICE_DIRS:
        device_dir = raw_dir / device_id
        device_dir.mkdir(parents=True, exist_ok=True)

        benign = pd.DataFrame(rng.standard_normal((n_benign, n_features)), columns=cols) # type: ignore
        benign.to_csv(device_dir / "benign_traffic.csv", index=False)

        attack_dir = device_dir / "gafgyt_attacks"
        attack_dir.mkdir(parents=True, exist_ok=True)
        attack = pd.DataFrame(rng.standard_normal((n_attack, n_features)), columns=cols) # type: ignore
        attack.to_csv(attack_dir / "combo.csv", index=False)


@pytest.mark.integration
class TestAllAlphaLevels:
    @pytest.fixture(autouse=True)
    def setup_synthetic_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.raw_dir = tmp_path / "raw"
        self.output_dir = tmp_path / "output"
        monkeypatch.setattr(
            regime_c_mod,
            "NBAIOT_SPEC",
            dataclasses.replace(NBAIOT_SPEC, feature_count=N_FEATURES),
        )
        _create_synthetic_nbaiot_raw(self.raw_dir)

    def test_all_alpha_levels(self) -> None:
        for alpha in ALPHA_LEVELS:
            result = partition_regime_c(
                raw_nbaiot_dir=self.raw_dir,
                output_dir=self.output_dir,
                alpha=alpha,
                seed=SEED,
                n_clients=N_CLIENTS,
                n_min=10, # Low threshold for synthetic data
                train_frac=TRAIN_FRAC,
                cal_frac=CAL_FRAC,
            )

            assert result.n_clients == N_CLIENTS, (
                f"α={alpha}: expected {N_CLIENTS} clients, got {result.n_clients}"
            )
            assert len(result.clients) == N_CLIENTS, (
                f"α={alpha}: expected {N_CLIENTS} client summaries, "
                f"got {len(result.clients)}"
            )

    def test_each_alpha_writes_client_directories(self) -> None:
        for alpha in ALPHA_LEVELS:
            partition_regime_c(
                raw_nbaiot_dir=self.raw_dir,
                output_dir=self.output_dir,
                alpha=alpha,
                seed=SEED,
                n_clients=N_CLIENTS,
                n_min=10,
                train_frac=TRAIN_FRAC,
                cal_frac=CAL_FRAC,
            )

            run_dir = (
                self.output_dir / "regime_c" / format_alpha_dir(alpha) / f"seed_{SEED}"
            )

            for i in range(N_CLIENTS):
                client_dir = run_dir / f"client_{i:02d}"
                assert (client_dir / filename_for_split(Split.TRAIN)).exists(), (
                    f"α={alpha}, client_{i:02d}: train.parquet missing"
                )
                assert (client_dir / filename_for_split(Split.CAL)).exists(), (
                    f"α={alpha}, client_{i:02d}: cal.parquet missing"
                )


@pytest.mark.integration
class TestJsDivergenceLogged:
    @pytest.fixture(autouse=True)
    def setup_synthetic_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.raw_dir = tmp_path / "raw"
        self.output_dir = tmp_path / "output"
        monkeypatch.setattr(
            regime_c_mod,
            "NBAIOT_SPEC",
            dataclasses.replace(NBAIOT_SPEC, feature_count=N_FEATURES),
        )
        _create_synthetic_nbaiot_raw(self.raw_dir)

    def test_js_divergence_logged(self) -> None:
        for alpha in ALPHA_LEVELS:
            partition_regime_c(
                raw_nbaiot_dir=self.raw_dir,
                output_dir=self.output_dir,
                alpha=alpha,
                seed=SEED,
                n_clients=N_CLIENTS,
                n_min=10,
                train_frac=TRAIN_FRAC,
                cal_frac=CAL_FRAC,
            )

            js_path = (
                self.output_dir
                / "regime_c"
                / format_alpha_dir(alpha)
                / f"seed_{SEED}"
                / "js_divergence.json"
            )
            assert js_path.exists(), f"α={alpha}: js_divergence.json not found"

            data = json.loads(js_path.read_text())
            assert "js_divergence" in data
            assert "alpha" in data
            assert "seed" in data
            assert data["js_divergence"] is None or isinstance(
                data["js_divergence"], float
            )
            assert data["js_divergence"] is None or data["js_divergence"] >= 0.0
            assert data["seed"] == SEED

    def test_js_divergence_monotonic(self) -> None:
        js_values: dict[float, float | None] = {}

        for alpha in ALPHA_LEVELS:
            result = partition_regime_c(
                raw_nbaiot_dir=self.raw_dir,
                output_dir=self.output_dir,
                alpha=alpha,
                seed=SEED,
                n_clients=N_CLIENTS,
                n_min=10,
                train_frac=TRAIN_FRAC,
                cal_frac=CAL_FRAC,
            )
            js_values[alpha] = result.js_divergence

        js_01 = js_values[0.1]
        js_10 = js_values[10.0]
        js_inf = js_values[math.inf]

        assert js_01 is not None, (
            "js_divergence must not be None with multiple clients"
        )
        assert js_10 is not None, (
            "js_divergence must not be None with multiple clients"
        )
        assert js_inf is not None, (
            "js_divergence must not be None with multiple clients"
        )
        assert js_01 > js_10, (
            f"Expected JS(α=0.1)={js_01:.4f} > "
            f"JS(α=10.0)={js_10:.4f}"
        )
        assert js_inf < js_01, (
            f"Expected JS(IID)={js_inf:.4f} < "
            f"JS(α=0.1)={js_01:.4f}"
        )


@pytest.mark.integration
class TestManifestContainsMixtures:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.raw_dir = tmp_path / "raw"
        self.output_dir = tmp_path / "output"
        monkeypatch.setattr(
            regime_c_mod,
            "NBAIOT_SPEC",
            dataclasses.replace(NBAIOT_SPEC, feature_count=N_FEATURES),
        )
        _create_synthetic_nbaiot_raw(self.raw_dir, n_benign=300, n_attack=60)
        self.result = partition_regime_c(
            raw_nbaiot_dir=self.raw_dir,
            output_dir=self.output_dir,
            alpha=0.5,
            seed=SEED,
            n_clients=N_CLIENTS,
            n_min=10,
            train_frac=TRAIN_FRAC,
            cal_frac=CAL_FRAC,
        )

    def test_manifest_has_client_summaries(self) -> None:
        run_dir = self.output_dir / "regime_c" / format_alpha_dir(0.5) / f"seed_{SEED}"
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists()
        payload = json.loads(manifest_path.read_text())
        assert "client_summaries" in payload["metadata"]
        assert len(payload["metadata"]["client_summaries"]) == N_CLIENTS

    def test_device_mixture_proportions_in_manifest(self) -> None:
        run_dir = self.output_dir / "regime_c" / format_alpha_dir(0.5) / f"seed_{SEED}"
        payload = json.loads((run_dir / "manifest.json").read_text())
        for cs in payload["metadata"]["client_summaries"]:
            assert "device_mixture_proportions" in cs
            mix = cs["device_mixture_proportions"]
            assert isinstance(mix, dict)
            assert len(mix) > 0
            total = sum(mix.values())
            assert abs(total - 1.0) < 1e-5, f"proportions sum to {total}, not 1"

    def test_device_mixture_proportions_sum_to_one(self) -> None:
        for client in self.result.clients:
            proportions = client.device_mixture_proportions
            assert len(proportions) > 0
            total = sum(proportions.values())
            assert abs(total - 1.0) < 1e-5, (
                f"client {client.client_id}: proportions sum to {total}"
            )

    def test_device_mixture_keys_are_valid_device_names(self) -> None:
        for client in self.result.clients:
            for key in client.device_mixture_proportions:
                assert key in DEVICE_DIRS
