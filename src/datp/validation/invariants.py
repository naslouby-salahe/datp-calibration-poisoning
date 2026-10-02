from __future__ import annotations

from datp.types import (
    ClientId,
    ContentHash,
    RandomSeed,
)


from dataclasses import dataclass

from datp.config.models import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES, ScoringStage, ThresholdPolicy
from datp.validation.enums import AuditStatus, InvariantField
from datp.validation.schemas import PolicyInvariantResult


@dataclass(frozen=True, slots=True)
class InvariantKey:

    stage: ExperimentStage
    seed: RandomSeed


@dataclass(frozen=True, slots=True)
class InvariantHashes:

    split_hash: ContentHash
    model_hash: ContentHash
    encoder_hash: ContentHash
    scoring_code_hash: ContentHash
    metrics_code_hash: ContentHash


@dataclass(frozen=True, slots=True)
class ScoreArtifactHash:
    stage: ScoringStage
    client_id: ClientId
    array_digest: ContentHash


def _check_hash_flags(hashes: list[InvariantHashes]) -> tuple[bool, bool, bool, bool]:
    sp_sh = len({h.split_hash for h in hashes}) <= 1
    mo_sh = len({h.model_hash for h in hashes} | {h.encoder_hash for h in hashes}) <= 1
    sc_sh = len({h.scoring_code_hash for h in hashes}) <= 1
    me_sh = len({h.metrics_code_hash for h in hashes}) <= 1
    return sp_sh, mo_sh, sc_sh, me_sh


def _resolve_invariant_status(
    sp_sh: bool,
    mo_sh: bool,
    sc_sh: bool,
    me_sh: bool,
    rec_sh: bool,
    rec_miss: bool,
    missing: list[ThresholdPolicy],
) -> tuple[AuditStatus, list[InvariantField]]:
    disallowed: list[InvariantField] = []
    if not sp_sh:
        disallowed.append(InvariantField.SPLIT_HASH)
    if not mo_sh:
        disallowed.append(InvariantField.MODEL_OR_ENCODER_HASH)
    if not sc_sh:
        disallowed.append(InvariantField.SCORING_CODE_HASH)
    if not me_sh:
        disallowed.append(InvariantField.METRICS_CODE_HASH)
    if not rec_sh and not rec_miss:
        disallowed.append(InvariantField.RECONSTRUCTION_ERROR_ARRAYS)
    if disallowed:
        return AuditStatus.FAIL, disallowed
    if missing or rec_miss:
        return AuditStatus.BLOCKED_PENDING_RUN, disallowed
    return AuditStatus.PASS, disallowed


def build_invariant_results(
    invariant_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]],
    score_hashes_by_cell: dict[
        InvariantKey, dict[ThresholdPolicy, frozenset[ScoreArtifactHash]]
    ],
) -> list[PolicyInvariantResult]:
    results: list[PolicyInvariantResult] = []

    for key, by_policy in sorted(
        invariant_inputs.items(), key=lambda i: (i[0].stage, i[0].seed)
    ):
        required = list(CONTROLLED_POLICIES)
        checked = [b for b in required if b in by_policy]
        missing = [b for b in required if b not in by_policy]

        hashes = [by_policy[b] for b in checked]
        sp_sh, mo_sh, sc_sh, me_sh = _check_hash_flags(hashes)

        cell_scores = score_hashes_by_cell.get(key, {})
        score_maps = [cell_scores[b] for b in checked if b in cell_scores]
        rec_miss = not score_maps
        rec_sh = all(m == score_maps[0] for m in score_maps) if score_maps else False

        status, disallowed = _resolve_invariant_status(
            sp_sh, mo_sh, sc_sh, me_sh, rec_sh, rec_miss, missing
        )

        results.append(
            PolicyInvariantResult(
                stage=key.stage,
                seed=key.seed,
                status=status,
                checked_policies=checked,
                missing_policies=missing,
                split_hash_shared=sp_sh,
                model_or_encoder_hash_shared=mo_sh,
                reconstruction_error_hashes_shared=rec_sh,
                scoring_code_hash_shared=sc_sh,
                metrics_code_hash_shared=me_sh,
                disallowed_differences=[v for v in disallowed],
            )
        )

    return results
