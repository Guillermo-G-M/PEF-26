import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder import cli
from dupfinder.generator import generate_dataset


def test_parse_args_defaults():
    args = cli._parse_args(["--modo", "baseline", "--path", "."])

    assert args.modo == "baseline"
    assert args.path == "."
    assert args.threshold == cli.DEFAULT_THRESHOLD_BYTES
    assert args.batch_size == cli.DEFAULT_BATCH_SIZE
    assert args.cache_file is None
    assert args.profile is False


def test_parse_args_rejects_invalid_modo():
    with pytest.raises(SystemExit):
        cli._parse_args(["--modo", "no_existe", "--path", "."])


def test_main_dispatches_to_chosen_mode(tmp_path, capsys):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=9)

    cli.main(["--modo", "baseline", "--path", str(tmp_path)])

    out = capsys.readouterr().out
    assert "modo=baseline" in out
    assert "archivos escaneados: 10" in out


def test_main_rejects_nonexistent_path(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["--modo", "baseline", "--path", str(tmp_path / "no_existe")])


def test_main_with_profile_prints_cprofile_stats(tmp_path, capsys):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=10)

    cli.main(["--modo", "baseline", "--path", str(tmp_path), "--profile"])

    out = capsys.readouterr().out
    assert "modo=baseline" in out
    assert "ncalls" in out
