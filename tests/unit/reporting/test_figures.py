from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from pathlib import Path

import numpy as np
from PIL import Image

from datp.config.compose import BASE_CONFIG
from datp.reporting.figures import (
    generate_figure1,
    generate_figure2,
    generate_figure3,
    generate_figure4,
)

RNG = np.random.default_rng(42)

DEVICE_NAMES = [f"device_{i}" for i in range(5)]


def _synthetic_per_device_fpr() -> dict[str, float]:
    return {d: float(RNG.uniform(0.01, 0.15)) for d in DEVICE_NAMES}


def test_figure1_creates_png(tmp_path: Path) -> None:
    fpr_global = _synthetic_per_device_fpr()
    fpr_local = _synthetic_per_device_fpr()
    path = generate_figure1(
        fpr_global, fpr_local, tmp_path, seed=0, style=BASE_CONFIG.reporting.style
    )
    assert path.exists()
    assert path.suffix == ".png"
    assert path.with_suffix(".pdf").exists()


def test_figure2_creates_png(tmp_path: Path) -> None:
    device_ids = ["dev_a", "dev_b", "dev_c"]
    cal_errors = {d: RNG.exponential(scale=0.5, size=200) for d in device_ids}
    tau_global = 1.2
    path = generate_figure2(
        cal_errors, tau_global, device_ids, tmp_path, style=BASE_CONFIG.reporting.style
    )
    assert path.exists()
    assert path.suffix == ".png"
    assert path.with_suffix(".pdf").exists()


def test_figure3_creates_png(tmp_path: Path) -> None:
    fpr_by_baseline = {
        ThresholdPolicy.GLOBAL_THRESHOLD: [
            RNG.uniform(0.01, 0.10, size=8) for _ in range(5)
        ],
        ThresholdPolicy.LOCAL_THRESHOLD: [
            RNG.uniform(0.005, 0.08, size=8) for _ in range(5)
        ],
        ThresholdPolicy.CLUSTER_THRESHOLD: [
            RNG.uniform(0.008, 0.09, size=8) for _ in range(5)
        ],
    }
    path = generate_figure3(
        fpr_by_baseline, tmp_path, style=BASE_CONFIG.reporting.style
    )
    assert path.exists()
    assert path.suffix == ".png"
    assert path.with_suffix(".pdf").exists()


def test_figure4_creates_png(tmp_path: Path) -> None:
    alphas = ["0.1", "0.3", "0.5", "1.0", "10.0", "iid"]
    cv_fpr_by_baseline = {
        ThresholdPolicy.GLOBAL_THRESHOLD: {
            a: list(RNG.uniform(0.2, 0.8, size=5)) for a in alphas
        },
        ThresholdPolicy.LOCAL_THRESHOLD: {
            a: list(RNG.uniform(0.1, 0.5, size=5)) for a in alphas
        },
        ThresholdPolicy.CLUSTER_THRESHOLD: {
            a: list(RNG.uniform(0.15, 0.6, size=5)) for a in alphas
        },
    }
    path = generate_figure4(
        cv_fpr_by_baseline, tmp_path, style=BASE_CONFIG.reporting.style
    )
    assert path.exists()
    assert path.suffix == ".png"
    assert path.with_suffix(".pdf").exists()


def test_figure_dpi_minimum(tmp_path: Path) -> None:
    fpr_global = _synthetic_per_device_fpr()
    fpr_local = _synthetic_per_device_fpr()
    path = generate_figure1(
        fpr_global, fpr_local, tmp_path, seed=99, style=BASE_CONFIG.reporting.style
    )
    img = Image.open(path)
    dpi = img.info.get("dpi", (72, 72))
    assert dpi[0] >= 299.99 and dpi[1] >= 299.99, f"DPI too low: {dpi}"
