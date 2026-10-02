from __future__ import annotations

from datp.types import (
    ClientId,
    FalsePositiveRate,
    NarrativeText,
    RandomSeed,
    RecordKey,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
)


from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Protocol, cast

import matplotlib
import numpy as np
from numpy.typing import NDArray

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datp.config.models import StyleConfig
from datp.core.enums import NBaIoTDevice, ThresholdPolicy
from datp.reporting.constants import NBAIOT_DEVICE_SHORT_LABELS
from datp.reporting.enums import FigureFileStem

plt.rcParams.update(
    {
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.family": "serif",
        "font.serif": [
            "Times New Roman",
            "Times",
            "Nimbus Roman No9 L",
            "DejaVu Serif",
        ],
        "mathtext.fontset": "stix",
    }
)

_FONT_SIZE_KEY = "font.size"


class _Patch(Protocol):
    def set_facecolor(self, color: str) -> None: ...
    def set_alpha(self, alpha: float) -> None: ...


class _BoxplotOutput(Protocol):
    def __getitem__(self, key: Literal["boxes"]) -> list[_Patch]: ...


class _Axes(Protocol):
    def bar(self, x: NDArray[np.generic], height: Sequence[float], width: float, *, label: str, color: str) -> None: ...
    def set(self, **kwargs: str) -> None: ...
    def set_xticks(self, ticks: NDArray[np.generic], labels: Sequence[str] | None = None) -> None: ...
    def set_xticklabels(self, labels: Sequence[str], **kwargs: str | float | int) -> None: ...
    def legend(self, **kwargs: str | float | int) -> None: ...
    def plot(self, x: NDArray[np.generic], y: NDArray[np.generic], **kwargs: str | float | int) -> None: ...
    def axvline(self, x: float, **kwargs: str | float | int) -> None: ...
    def boxplot(self, data: Sequence[NDArray[np.generic]], **kwargs: bool | Sequence[str]) -> _BoxplotOutput: ...
    def tick_params(self, *, axis: str, **kwargs: str | float | int) -> None: ...
    def fill_between(self, x: NDArray[np.generic], y1: NDArray[np.generic], y2: NDArray[np.generic], **kwargs: str | float | int) -> None: ...
    def errorbar(self, x: Sequence[float], y: Sequence[float], **kwargs: str | float | int | Sequence[Sequence[float]]) -> None: ...
    def axhline(self, y: float, **kwargs: str | float | int) -> None: ...
    def scatter(self, x: NDArray[np.generic], y: NDArray[np.generic], **kwargs: str | float | int) -> None: ...
    def hlines(self, y: float, xmin: float, xmax: float, **kwargs: str | float | int) -> None: ...


class _Figure(Protocol):
    def savefig(
        self, fname: Path, *, dpi: int | None = None, bbox_inches: str | None = None
    ) -> None: ...
    def tight_layout(self) -> None: ...


def _save_figs(fig: plt.Figure, base_path: Path, dpi: SignedCount) -> Path:
    figure = cast(_Figure, fig)
    figure.savefig(base_path.with_suffix(".png"), dpi=dpi, bbox_inches="tight")
    figure.savefig(base_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return base_path.with_suffix(".png")


def generate_figure1(
    per_device_fpr_global: dict[ClientId, FalsePositiveRate],
    per_device_fpr_local: dict[ClientId, FalsePositiveRate],
    output_dir: Path,
    seed: RandomSeed,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    devices = sorted(per_device_fpr_global.keys())
    x, width = np.arange(len(devices)), 0.35
    fig, ax = plt.subplots(figsize=style.figsize_double_col)
    ax = cast(_Axes, ax)

    for offset, data, pol in [
        (-width / 2, per_device_fpr_global, ThresholdPolicy.GLOBAL_THRESHOLD),
        (width / 2, per_device_fpr_local, ThresholdPolicy.LOCAL_THRESHOLD),
    ]:
        ax.bar(
            x + offset,
            [data[d] for d in devices],
            width,
            label=style.policy_labels[pol],
            color=style.policy_colors[pol],
        )

    ax.set(xlabel="Device", ylabel="FPR")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [NBAIOT_DEVICE_SHORT_LABELS[NBaIoTDevice(d)] for d in devices],
        rotation=45,
        ha="right",
        fontsize=style.font_size - 1,
    )
    ax.legend()
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / f"{FigureFileStem.FIGURE_1}{seed}", style.dpi)


def generate_figure2(
    cal_errors: dict[ClientId, ScoreVector],
    tau_global: Threshold,
    device_ids: list[ClientId],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_double_col)
    ax = cast(_Axes, ax)
    all_vals = np.concatenate([cal_errors[d] for d in device_ids if d in cal_errors])
    x_clip = float(np.percentile(all_vals, 99))

    for dev_id in device_ids:
        if dev_id not in cal_errors:
            continue
        errors = np.sort(cal_errors[dev_id])
        ecdf_y = np.arange(1, len(errors) + 1) / len(errors)
        mask = errors <= x_clip
        ax.plot(
            errors[mask],
            ecdf_y[mask],
            label=NBAIOT_DEVICE_SHORT_LABELS[NBaIoTDevice(dev_id)],
            linewidth=1.4,
        )

    ax.axvline(
        tau_global,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="GLOBAL_THRESHOLD client-averaged threshold",
    )
    ax.set(xlabel="Reconstruction Error", ylabel="ECDF")
    ax.legend(fontsize=style.font_size - 1)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureFileStem.FIGURE_2, style.dpi)


def generate_figure3(
    fpr_by_policy: dict[ThresholdPolicy, list[ScoreVector]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_single_col)
    ax = cast(_Axes, ax)
    policies = sorted(fpr_by_policy.keys())

    bp = ax.boxplot(
        [np.concatenate(fpr_by_policy[b]) for b in policies],
        tick_labels=[style.policy_labels[b] for b in policies],
        patch_artist=True,
    )
    for patch, color in zip(bp["boxes"], [style.policy_colors[b] for b in policies]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set(
        ylabel="FPR", title="Per-client FPR Distribution (eligible clients, 10 seeds)"
    )
    ax.tick_params(axis="x", labelrotation=30)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureFileStem.FIGURE_3, style.dpi)


def generate_figure5(
    client_effects: dict[NarrativeText, dict[ThresholdPolicy, dict[ClientId, list[ScoreValue]]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    panels = list(client_effects)
    fig, axes = plt.subplots(
        1, len(panels), figsize=style.figsize_double_col, squeeze=False
    )
    for raw_ax, label in zip(axes[0], panels):
        ax = cast(_Axes, raw_ax)
        by_policy = client_effects[label]
        victims = sorted({v for per in by_policy.values() for v in per})
        policies = sorted(by_policy)
        width = 0.8 / max(len(policies), 1)
        for i, pol in enumerate(policies):
            xs: list[ScoreValue] = []
            means: list[ScoreValue] = []
            lows: list[ScoreValue] = []
            highs: list[ScoreValue] = []
            for j, v in enumerate(victims):
                vals = by_policy[pol].get(v)
                if not vals:
                    continue
                xs.append(j + (i - (len(policies) - 1) / 2) * width)
                means.append(float(np.mean(vals)))
                lows.append(float(np.mean(vals)) - min(vals))
                highs.append(max(vals) - float(np.mean(vals)))
            ax.errorbar(
                xs,
                means,
                yerr=[lows, highs],
                fmt="o",
                markersize=3,
                capsize=2,
                linewidth=1.0,
                color=style.policy_colors[pol],
                label=style.policy_labels[pol],
            )
        ax.axhline(0.0, color="black", linewidth=0.6)
        ax.set_xticks(np.arange(len(victims)))
        ax.set_xticklabels(
            [NBAIOT_DEVICE_SHORT_LABELS[NBaIoTDevice(v)] for v in victims],
            rotation=60,
            ha="right",
            fontsize=style.font_size - 2,
        )
        ax.set(ylabel=label)
    cast(_Axes, axes[0][0]).legend(fontsize=style.font_size - 2)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureFileStem.FIGURE_5, style.dpi)


def generate_figure6(
    seed_effects: dict[RecordKey, dict[ThresholdPolicy, list[ScoreValue]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    panels = list(seed_effects)
    fig, axes = plt.subplots(
        1, len(panels), figsize=style.figsize_double_col, squeeze=False
    )
    rng = np.random.default_rng(0)
    for raw_ax, label in zip(axes[0], panels):
        ax = cast(_Axes, raw_ax)
        by_policy = seed_effects[label]
        policies = sorted(by_policy)
        for i, pol in enumerate(policies):
            vals = np.asarray(by_policy[pol], dtype=np.float64)
            ax.scatter(
                i + rng.uniform(-0.12, 0.12, vals.size),
                vals,
                s=14,
                color=style.policy_colors[pol],
                alpha=0.8,
            )
            ax.hlines(
                float(np.nanmean(vals)), i - 0.3, i + 0.3, color="black", linewidth=1.2
            )
        ax.axhline(0.0, color="black", linewidth=0.6, linestyle=":")
        ax.set_xticks(np.arange(len(policies)))
        ax.set_xticklabels(
            [style.policy_labels[p] for p in policies],
            rotation=30,
            ha="right",
            fontsize=style.font_size - 2,
        )
        ax.set(ylabel=label)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureFileStem.FIGURE_6, style.dpi)
