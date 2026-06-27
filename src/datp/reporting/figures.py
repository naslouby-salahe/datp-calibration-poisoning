"""Matplotlib figure generators for paper figures 1–4."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datp.config.models import StyleConfig
from datp.core.enums import ThresholdPolicy
from datp.reporting.constants import (
    FIGURE1_STEM,
    FIGURE2_STEM,
    FIGURE3_STEM,
    FIGURE4_STEM,
    NBAIOT_DEVICE_SHORT_LABELS,
)

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


def _save_figs(fig: plt.Figure, base_path: Path, dpi: int) -> Path:
    fig.savefig(base_path.with_suffix(".png"), dpi=dpi, bbox_inches="tight")
    fig.savefig(base_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return base_path.with_suffix(".png")


def generate_figure1(
    per_device_fpr_global: dict[str, float],
    per_device_fpr_local: dict[str, float],
    output_dir: Path,
    seed: int,
    style: StyleConfig,
) -> Path:
    """Generate a grouped bar chart of per-device FPR under GLOBAL vs LOCAL thresholds (Figure 1)."""
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    devices = sorted(per_device_fpr_global.keys())
    x, width = np.arange(len(devices)), 0.35
    fig, ax = plt.subplots(figsize=style.figsize_double_col)

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
        [NBAIOT_DEVICE_SHORT_LABELS.get(d, d.replace("_", " ")) for d in devices],
        rotation=45,
        ha="right",
        fontsize=style.font_size - 1,
    )
    ax.legend()
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / f"{FIGURE1_STEM}{seed}", style.dpi)


def generate_figure2(
    cal_errors: dict[str, np.ndarray],
    tau_global: float,
    device_ids: list[str],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    """Generate per-device eCDF plots of calibration errors with global threshold (Figure 2)."""
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_double_col)
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
            label=NBAIOT_DEVICE_SHORT_LABELS.get(dev_id, dev_id.replace("_", " ")),
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
    return _save_figs(fig, output_dir / FIGURE2_STEM, style.dpi)


def generate_figure3(
    fpr_by_policy: dict[ThresholdPolicy, list[np.ndarray]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    """Generate a boxplot comparing per-client FPR distributions across policies (Figure 3)."""
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_single_col)
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
    return _save_figs(fig, output_dir / FIGURE3_STEM, style.dpi)


def generate_figure4(
    cv_fpr_by_policy: dict[ThresholdPolicy, dict[str, list[float]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    """Generate a line plot of CV(FPR) vs Dirichlet alpha across policies (Figure 4)."""
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    policies = sorted(cv_fpr_by_policy.keys())
    all_alpha_keys = sorted({a for b in policies for a in cv_fpr_by_policy[b]})
    fig, ax = plt.subplots(figsize=style.figsize_double_col)

    for b in policies:
        alpha_map = cv_fpr_by_policy[b]
        alpha_order = [a for a in all_alpha_keys if a in alpha_map]
        x = np.arange(len(alpha_order), dtype=np.float64)
        means_arr = np.array([float(np.mean(alpha_map[a])) for a in alpha_order])
        stds_arr = np.array(
            [
                float(np.std(alpha_map[a], ddof=1)) if len(alpha_map[a]) > 1 else 0.0
                for a in alpha_order
            ]
        )
        color = style.policy_colors[b]

        ax.plot(
            x,
            means_arr,
            marker="o",
            markersize=3,
            color=color,
            label=style.policy_labels[b],
        )
        ax.fill_between(
            x, means_arr - stds_arr, means_arr + stds_arr, color=color, alpha=0.2
        )

    ax.set_xticks(np.arange(len(all_alpha_keys)), all_alpha_keys)
    ax.set(
        xlabel=r"Dirichlet $\alpha$ / IID reference",
        ylabel="CV(FPR)",
        title="CV(FPR) comparison",
    )
    ax.legend(fontsize=style.font_size - 1)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FIGURE4_STEM, style.dpi)
