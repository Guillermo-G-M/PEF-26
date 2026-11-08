import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.generator import generate_dataset
from dupfinder.modes import parallel_mode, structural


def _as_sets(groups):
    return {frozenset(g) for g in groups}


def test_matches_structural(tmp_path):
    generate_dataset(tmp_path, count=50, dup_ratio=0.3, min_size=200, max_size=20_000, seed=7)

    struct_groups, struct_n, _ = structural.find_duplicates(tmp_path)
    par_groups, par_n, _ = parallel_mode.find_duplicates(tmp_path, workers=2)

    assert par_n == struct_n
    assert _as_sets(par_groups) == _as_sets(struct_groups)


def test_matches_with_single_worker(tmp_path):
    generate_dataset(tmp_path, count=30, dup_ratio=0.3, min_size=200, max_size=20_000, seed=8)

    groups1, _, _ = parallel_mode.find_duplicates(tmp_path, workers=1)
    groups4, _, _ = parallel_mode.find_duplicates(tmp_path, workers=4)

    assert _as_sets(groups1) == _as_sets(groups4)


def test_no_lost_duplicates_under_many_workers(tmp_path):
    generate_dataset(tmp_path, count=100, dup_ratio=0.3, min_size=500, max_size=500, seed=9)

    groups, n, _ = parallel_mode.find_duplicates(tmp_path, workers=4)

    assert n == 100
    assert sum(len(g) - 1 for g in groups) == int(100 * 0.3)


def test_handles_nonpositive_workers(tmp_path):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=1)

    groups, n, _ = parallel_mode.find_duplicates(tmp_path, workers=0)

    assert n == 10
    assert sum(len(g) - 1 for g in groups) == 2


def test_no_duplicates(tmp_path):
    generate_dataset(tmp_path, count=6, dup_ratio=0.0, min_size=128, max_size=512, seed=2)

    groups, n, _ = parallel_mode.find_duplicates(tmp_path, workers=2)

    assert n == 6
    assert groups == []


def test_empty_directory(tmp_path):
    groups, n, n_hashed = parallel_mode.find_duplicates(tmp_path, workers=2)

    assert n == 0
    assert n_hashed == 0
    assert groups == []


def test_hash_one_returns_path_and_digest(tmp_path):
    sample = tmp_path / "f.bin"
    sample.write_bytes(b"contenido")

    path, digest = parallel_mode._hash_one(sample)

    assert path == sample
    assert digest == structural.hash_file(sample)


def test_run_prints_report(tmp_path, capsys):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=5)

    parallel_mode.run(tmp_path, workers=2, threshold=0)

    out = capsys.readouterr().out
    assert "modo=paralelo" in out
    assert "workers: 2" in out


def test_run_rejects_nonexistent_path(tmp_path):
    with pytest.raises(SystemExit):
        parallel_mode.run(tmp_path / "no_existe", workers=2, threshold=0)
