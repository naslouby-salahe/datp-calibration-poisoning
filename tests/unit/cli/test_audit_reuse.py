from pathlib import Path

from datp.cli import audit
from datp.config.compose import BASE_CONFIG
from datp.validation.schemas import VerdictSummary, VerdictTable


def test_reuse_command_runs_and_writes_reuse_verdicts(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[Path, Path | None, object, bool]] = []

    def compute_all_verdicts(
        base_dir: Path,
        *,
        data_root: Path | None,
        config: object,
        write_reports: bool,
    ) -> VerdictTable:
        calls.append((base_dir, data_root, config, write_reports))
        return VerdictTable(
            cells=[],
            summary=VerdictSummary(
                total=0,
                verified_reuse_safe=0,
                reuse_blocked_rerun_required=0,
                by_stage={},
            ),
        )

    monkeypatch.setattr(audit, "compute_all_verdicts", compute_all_verdicts)

    audit.reuse(base_dir=tmp_path, data_root=tmp_path / "data")

    assert calls == [(tmp_path, tmp_path / "data", BASE_CONFIG, True)]
