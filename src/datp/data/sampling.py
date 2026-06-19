from __future__ import annotations

import polars as pl

_COUNT_COLUMN = "len"
_EXACT_COLUMN = "exact"
_FLOOR_COLUMN = "floor"
_REMAINDER_COLUMN = "remainder"
_FINAL_ALLOC_COLUMN = "final_alloc"
_INDEX_COLUMN = "index"


def _allocate_attack_counts(
    attack_df: pl.DataFrame,
    attack_budget: int,
    label_column: str,
) -> dict[str, int]:
    counts = attack_df.group_by(label_column).len().sort(label_column)
    total_attack = len(attack_df)

    exact_counts = counts.with_columns(
        **{_EXACT_COLUMN: pl.col(_COUNT_COLUMN) * attack_budget / total_attack}
    )
    exact_counts = exact_counts.with_columns(
        **{
            _FLOOR_COLUMN: pl.col(_EXACT_COLUMN).floor().cast(pl.Int64),
            _REMAINDER_COLUMN: (pl.col(_EXACT_COLUMN) - pl.col(_EXACT_COLUMN).floor()),
        }
    )

    allocated_so_far = exact_counts[_FLOOR_COLUMN].sum()
    remaining = attack_budget - allocated_so_far

    exact_counts = exact_counts.sort(_REMAINDER_COLUMN, descending=True)
    exact_counts = exact_counts.with_row_index(_INDEX_COLUMN)
    exact_counts = exact_counts.with_columns(
        **{
            _FINAL_ALLOC_COLUMN: pl.when(pl.col(_INDEX_COLUMN) < remaining)
            .then(pl.col(_FLOOR_COLUMN) + 1)
            .otherwise(pl.col(_FLOOR_COLUMN))
        }
    )

    return dict(zip(exact_counts[label_column], exact_counts[_FINAL_ALLOC_COLUMN]))


def _sample_attack_rows(
    attack_df: pl.DataFrame,
    attack_budget: int,
    label_column: str,
    seed: int,
) -> pl.DataFrame:
    if len(attack_df) <= attack_budget:
        return attack_df
    if attack_budget <= 0:
        return attack_df.clear()

    alloc_dict = _allocate_attack_counts(attack_df, attack_budget, label_column)
    sampled_parts = []
    for cat, group in attack_df.group_by(label_column):
        n_sample = alloc_dict.get(cat[0], 0)
        if n_sample > 0:
            sampled_parts.append(
                group.sample(n=n_sample, seed=seed, with_replacement=False)
            )

    return pl.concat(sampled_parts) if sampled_parts else attack_df.clear()


def apply_ciciot_cap(
    df: pl.DataFrame,
    cap: int,
    label_column: str,
    benign_label: str,
    attack_reserve_fraction: float,
    seed: int,
) -> pl.DataFrame:
    """Deterministic priority-order cap: attack rows capped to attack_reserve; benign fills remaining budget."""
    attack_mask = df[label_column] != benign_label
    benign_df = df.filter(~attack_mask)
    attack_df = df.filter(attack_mask)

    attack_budget = min(len(attack_df), int(cap * attack_reserve_fraction))
    sampled_attack = _sample_attack_rows(attack_df, attack_budget, label_column, seed)

    benign_budget = cap - len(sampled_attack)
    if len(benign_df) <= benign_budget:
        sampled_benign = benign_df
    else:
        sampled_benign = benign_df.sample(
            n=benign_budget, seed=seed, with_replacement=False
        )

    return pl.concat([sampled_benign, sampled_attack])
