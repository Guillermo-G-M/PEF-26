import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.generator import generate_dataset
from dupfinder.modes import baseline
from dupfinder.modes.baseline import find_duplicates


def test_finds_all_redundant_files(tmp_path):
    generate_dataset(tmp_path, count=10, dup_ratio=0.5, min_size=256, max_size=256, seed=1)

    groups, n = find_duplicates(tmp_path)

    assert n == 10
    assert sum(len(g) - 1 for g in groups) == 5
    for group in groups:
        contents = {p.read_bytes() for p in group}
        assert len(contents) == 1


def test_no_duplicates(tmp_path):
    generate_dataset(tmp_path, count=6, dup_ratio=0.0, min_size=128, max_size=512, seed=2)

    groups, n = find_duplicates(tmp_path)

    assert n == 6
    assert groups == []


def test_empty_directory(tmp_path):
    groups, n = find_duplicates(tmp_path)

    assert n == 0
    assert groups == []


def test_run_prints_report(tmp_path, capsys):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=5)

    baseline.run(tmp_path, workers=1, threshold=0)

    out = capsys.readouterr().out
    assert "modo=baseline" in out
    assert "archivos escaneados: 10" in out


def test_run_rejects_nonexistent_path(tmp_path):
    with pytest.raises(SystemExit):
        baseline.run(tmp_path / "no_existe", workers=1, threshold=0)
