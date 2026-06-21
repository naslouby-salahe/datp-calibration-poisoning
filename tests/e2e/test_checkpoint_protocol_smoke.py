from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from datp.app.cli import app


def test_checkpoint_protocol_smoke_cli_uses_temp_root(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "checkpoint-protocol",
            "smoke",
            "--artifact-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["rounds"] == [25, 50]
    assert payload["selected_round"] in {25, 50}
    assert (tmp_path / "scores" / "a" / "seed_0" / "round_25").is_dir()
    assert (
        tmp_path / "results" / "a" / "global_threshold" / "seed_0" / "round_25"
    ).is_dir()
    assert "outputs" not in tmp_path.parts


def test_checkpoint_protocol_smoke_cli_rejects_outputs_child() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "checkpoint-protocol",
            "smoke",
            "--artifact-root",
            "outputs/checkpoint_protocol_smoke",
        ],
    )

    assert result.exit_code != 0
    assert "must not write to outputs" in result.output
