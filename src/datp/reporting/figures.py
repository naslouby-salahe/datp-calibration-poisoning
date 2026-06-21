from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from datp.config.models import StyleConfig
from datp.reporting.constants import (
    FIGURE1_STEM,
    FIGURE2_STEM,
    FIGURE3_STEM,
    FIGURE4_STEM,
    NBAIOT_DEVICE_SHORT_LABELS,
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


def _policy_label(policy: ThresholdPolicy, style: StyleConfig) -> str:
    return style.policy_labels[policy]


def _policy_color(policy: ThresholdPolicy, style: StyleConfig) -> str:
    return style.policy_colors[policy]


def generate_figure1(
    per_device_fpr_global: dict[str, float],
    per_device_fpr_local: dict[str, float],
    output_dir: Path,
    seed: int,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size  # type: ignore[index]

    devices = sorted(per_device_fpr_global.keys())
    fpr_global = [per_device_fpr_global[d] for d in devices]
    fpr_local = [per_device_fpr_local[d] for d in devices]
    labels = [NBAIOT_DEVICE_SHORT_LABELS.get(d, d.replace("_", " ")) for d in devices]

    x = np.arange(len(devices))
    width = 0.35

    fig, ax = plt.subplots(figsize=style.figsize_double_col)
    ax.bar(
        x - width / 2,
        fpr_global,
        width,
        label=_policy_label(ThresholdPolicy.GLOBAL_THRESHOLD, style),
        color=_policy_color(ThresholdPolicy.GLOBAL_THRESHOLD, style),
    )
    ax.bar(
        x + width / 2,
        fpr_local,
        width,
        label=_policy_label(ThresholdPolicy.LOCAL_THRESHOLD, style),
        color=_policy_color(ThresholdPolicy.LOCAL_THRESHOLD, style),
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
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size  # type: ignore[index]
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
        label="GLOBAL_THRESHOLD client-averaged threshold",
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
    fpr_by_policy: dict[ThresholdPolicy, list[np.ndarray]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    policies = sorted(fpr_by_policy.keys())
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size  # type: ignore[index]

    fig, ax = plt.subplots(figsize=style.figsize_single_col)

    data = []
    labels = []
    colors = []
    for b in policies:
        combined = np.concatenate(fpr_by_policy[b])
        data.append(combined)
        labels.append(_policy_label(b, style))
        colors.append(_policy_color(b, style))

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
    cv_fpr_by_policy: dict[ThresholdPolicy, dict[str, list[float]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    policies = sorted(cv_fpr_by_policy.keys())
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size  # type: ignore[index]

    all_alpha_keys: list[str] = []
    for b in policies:
        for a in cv_fpr_by_policy[b]:
            if a not in all_alpha_keys:
                all_alpha_keys.append(a)
    all_alpha_keys.sort()

    fig, ax = plt.subplots(figsize=style.figsize_double_col)

    for b in policies:
        alpha_map = cv_fpr_by_policy[b]
        alpha_order = [a for a in all_alpha_keys if a in alpha_map]
        x = np.arange(len(alpha_order), dtype=np.float64)
        means = [float(np.mean(alpha_map[a])) for a in alpha_order]
        stds = [
            float(np.std(alpha_map[a], ddof=1)) if len(alpha_map[a]) > 1 else 0.0
            for a in alpha_order
        ]
        means_arr = np.array(means)
        stds_arr = np.array(stds)

        color = _policy_color(b, style)
        label = _policy_label(b, style)
        ax.plot(x, means, marker="o", markersize=3, color=color, label=label)
        ax.fill_between(
            x,
            means_arr - stds_arr,
            means_arr + stds_arr,
            color=color,
            alpha=0.2,
        )

    ax.set_xticks(np.arange(len(all_alpha_keys)), all_alpha_keys)
    ax.set_xlabel(r"Dirichlet $\alpha$ / IID reference")
    ax.set_ylabel("CV(FPR)")
    ax.set_title(r"CV(FPR) comparison")
    ax.legend(fontsize=style.font_size - 1)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{FIGURE4_STEM}.png"
    fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
    fig.savefig(output_dir / f"{FIGURE4_STEM}.pdf", bbox_inches="tight")
    plt.close(fig)
    return path
