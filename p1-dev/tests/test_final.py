import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.generator import generate_dataset
from dupfinder.modes import final, structural


def _as_sets(groups):
    return {frozenset(g) for g in groups}


def test_matches_structural_with_empty_cache(tmp_path):
    generate_dataset(tmp_path, count=50, dup_ratio=0.3, min_size=200, max_size=20_000, seed=7)

    struct_groups, struct_n, _ = structural.find_duplicates(tmp_path)
    final_groups, final_n, hits, n_threads, n_processes = final.find_duplicates(
        tmp_path, workers=2, threshold=5_000, cache={}
    )

    assert final_n == struct_n
    assert _as_sets(final_groups) == _as_sets(struct_groups)
    assert hits == 0
    assert n_threads + n_processes > 0


def test_routes_by_threshold(tmp_path):
    (tmp_path / "small_a.bin").write_bytes(b"a" * 100)
    (tmp_path / "small_b.bin").write_bytes(b"a" * 100)
    (tmp_path / "big_a.bin").write_bytes(b"b" * 10_000)
    (tmp_path / "big_b.bin").write_bytes(b"b" * 10_000)

    groups, n, hits, n_threads, n_processes = final.find_duplicates(
        tmp_path, workers=2, threshold=1_000, cache={}
    )

    assert n == 4
    assert hits == 0
    assert n_threads == 2
    assert n_processes == 2
    assert _as_sets(groups) == {
        frozenset([tmp_path / "small_a.bin", tmp_path / "small_b.bin"]),
        frozenset([tmp_path / "big_a.bin", tmp_path / "big_b.bin"]),
    }


def test_second_scan_reuses_cache(tmp_path):
    generate_dataset(tmp_path, count=40, dup_ratio=0.25, min_size=200, max_size=20_000, seed=11)

    cache = {}
    groups1, _, hits1, _, _ = final.find_duplicates(
        tmp_path, workers=2, threshold=5_000, cache=cache
    )
    groups2, _, hits2, n_threads2, n_processes2 = final.find_duplicates(
        tmp_path, workers=2, threshold=5_000, cache=cache
    )

    assert hits1 == 0
    assert n_threads2 == 0
    assert n_processes2 == 0
    assert hits2 > 0
    assert _as_sets(groups1) == _as_sets(groups2)


def test_handles_nonpositive_workers(tmp_path):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=1)

    groups, n, _hits, _n_threads, _n_processes = final.find_duplicates(
        tmp_path, workers=0, threshold=5_000, cache={}
    )

    assert n == 10
    assert sum(len(g) - 1 for g in groups) == 2


def test_no_duplicates(tmp_path):
    generate_dataset(tmp_path, count=6, dup_ratio=0.0, min_size=128, max_size=512, seed=2)

    groups, n, _hits, _n_threads, _n_processes = final.find_duplicates(
        tmp_path, workers=2, threshold=5_000, cache={}
    )

    assert n == 6
    assert groups == []


def test_empty_directory(tmp_path):
    groups, n, hits, n_threads, n_processes = final.find_duplicates(
        tmp_path, workers=2, threshold=5_000, cache={}
    )

    assert n == 0
    assert hits == 0
    assert n_threads == 0
    assert n_processes == 0
    assert groups == []


def test_run_prints_report(tmp_path, capsys):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=5)
    cache_path = tmp_path.parent / "run_final_cache.json"

    final.run(tmp_path, workers=2, threshold=0, cache_file=cache_path)

    out = capsys.readouterr().out
    assert "modo=final" in out
    assert "ruteo (umbral)" in out


def test_run_rejects_nonexistent_path(tmp_path):
    with pytest.raises(SystemExit):
        final.run(tmp_path / "no_existe", workers=2, threshold=0)
