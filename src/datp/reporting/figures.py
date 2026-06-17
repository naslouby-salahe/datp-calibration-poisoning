from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from datp.config.models import StyleConfig
from datp.core.enums import Baseline
from datp.reporting.constants import (
    FIGURE1_STEM,
    FIGURE2_STEM,
    FIGURE3_STEM,
    FIGURE4_STEM,
    NBAIOT_DEVICE_SHORT_LABELS,
    REGIME_C_ALPHA_DISPLAY_ORDER,
    REGIME_C_ALPHA_TICK_LABELS,
)

# Embedded fonts for IEEE compliance.
_FONT_SIZE_KEY = "font.size"
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


def _baseline_label(baseline: Baseline, style: StyleConfig) -> str:
    return style.baseline_labels[baseline]


def _baseline_color(baseline: Baseline, style: StyleConfig) -> str:
    return style.baseline_colors[baseline]


def generate_figure1(
    per_device_fpr_b1: dict[str, float],
    per_device_fpr_b2: dict[str, float],
    output_dir: Path,
    seed: int,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size

    devices = sorted(per_device_fpr_b1.keys())
    fpr_b1 = [per_device_fpr_b1[d] for d in devices]
    fpr_b2 = [per_device_fpr_b2[d] for d in devices]
    labels = [NBAIOT_DEVICE_SHORT_LABELS.get(d, d.replace("_", " ")) for d in devices]

    x = np.arange(len(devices))
    width = 0.35

    fig, ax = plt.subplots(figsize=style.figsize_double_col)
    ax.bar(
        x - width / 2,
        fpr_b1,
        width,
        label=_baseline_label(Baseline.B1, style),
        color=_baseline_color(Baseline.B1, style),
    )
    ax.bar(
        x + width / 2,
        fpr_b2,
        width,
        label=_baseline_label(Baseline.B2, style),
        color=_baseline_color(Baseline.B2, style),
    )

    ax.set_xlabel("Device")
    ax.set_ylabel("FPR")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=style.font_size - 1)
    ax.legend()
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{FIGURE1_STEM}{seed}"
    path = output_dir / f"{stem}.png"
    fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    return path


def generate_figure2(
    cal_errors: dict[str, np.ndarray],
    tau_global: float,
    device_ids: list[str],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    """x-axis is clipped at the 99th percentile across plotted devices."""
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_double_col)

    all_vals = np.concatenate([cal_errors[d] for d in device_ids if d in cal_errors])
    x_clip = float(np.percentile(all_vals, 99))

    for dev_id in device_ids:
        if dev_id not in cal_errors:
            continue
        errors = np.sort(cal_errors[dev_id])
        n = len(errors)
        ecdf_x = errors
        ecdf_y = np.arange(1, n + 1) / n
        mask = ecdf_x <= x_clip
        ax.plot(
            ecdf_x[mask],
            ecdf_y[mask],
            label=NBAIOT_DEVICE_SHORT_LABELS.get(dev_id, dev_id.replace("_", " ")),
            linewidth=1.4,
        )

    ax.axvline(
        tau_global,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="B1 client-averaged threshold",
    )
    ax.set_xlabel("Reconstruction Error")
    ax.set_ylabel("ECDF")
    ax.legend(fontsize=style.font_size - 1)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{FIGURE2_STEM}.png"
    fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
    fig.savefig(output_dir / f"{FIGURE2_STEM}.pdf", bbox_inches="tight")
    plt.close(fig)
    return path


def generate_figure3(
    fpr_by_baseline: dict[Baseline, list[np.ndarray]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    baselines = sorted(fpr_by_baseline.keys())
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size

    fig, ax = plt.subplots(figsize=style.figsize_single_col)

    data = []
    labels = []
    colors = []
    for b in baselines:
        combined = np.concatenate(fpr_by_baseline[b])
        data.append(combined)
        labels.append(_baseline_label(b, style))
        colors.append(_baseline_color(b, style))

    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)
    for patch, color in zip(bp["boxes"], colors, strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel("FPR")
    ax.set_title("Per-client FPR Distribution (eligible clients, 5 seeds)")
    ax.tick_params(axis="x", labelrotation=30)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{FIGURE3_STEM}.png"
    fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
    fig.savefig(output_dir / f"{FIGURE3_STEM}.pdf", bbox_inches="tight")
    plt.close(fig)
    return path


def generate_figure4(
    cv_fpr_by_baseline: dict[Baseline, dict[str, list[float]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    baselines = sorted(cv_fpr_by_baseline.keys())
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size

    fig, ax = plt.subplots(figsize=style.figsize_double_col)

    for b in baselines:
        alpha_map = cv_fpr_by_baseline[b]
        alpha_order = [a for a in REGIME_C_ALPHA_DISPLAY_ORDER if a in alpha_map]
        x = np.arange(len(alpha_order), dtype=np.float64)
        means = [float(np.mean(alpha_map[a])) for a in alpha_order]
        stds = [
            float(np.std(alpha_map[a], ddof=1)) if len(alpha_map[a]) > 1 else 0.0
            for a in alpha_order
        ]
        means_arr = np.array(means)
        stds_arr = np.array(stds)

        color = _baseline_color(b, style)
        label = _baseline_label(b, style)
        ax.plot(x, means, marker="o", markersize=3, color=color, label=label)
        ax.fill_between(
            x,
            means_arr - stds_arr,
            means_arr + stds_arr,
            color=color,
            alpha=0.2,
        )

    ax.set_xticks(
        np.arange(len(REGIME_C_ALPHA_TICK_LABELS)), list(REGIME_C_ALPHA_TICK_LABELS)
    )
    ax.set_xlabel(r"Dirichlet $\alpha$ / IID reference")
    ax.set_ylabel("CV(FPR)")
    ax.set_title(r"CV(FPR) vs. Dirichlet $\alpha$ (Regime C)")
    ax.legend(fontsize=style.font_size - 1)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{FIGURE4_STEM}.png"
    fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
    fig.savefig(output_dir / f"{FIGURE4_STEM}.pdf", bbox_inches="tight")
    plt.close(fig)
    return path
