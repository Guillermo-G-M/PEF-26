import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.concurrency import _batches
from dupfinder.generator import generate_dataset
from dupfinder.modes import concurrent_mode, final, parallel_mode


def _as_sets(groups):
    return {frozenset(g) for g in groups}


def test_batches_splits_into_expected_chunks():
    items = list(range(10))

    assert list(_batches(items, 3)) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    assert list(_batches(items, 10)) == [items]
    assert list(_batches(items, 100)) == [items]
    assert list(_batches(items, None)) == [items]
    assert list(_batches(items, 0)) == [items]
    assert list(_batches([], 3)) == []


def test_concurrent_mode_batching_matches_unbatched(tmp_path):
    generate_dataset(tmp_path, count=60, dup_ratio=0.3, min_size=200, max_size=5_000, seed=21)

    groups_full, n_full, _ = concurrent_mode.find_duplicates(tmp_path, workers=4, batch_size=None)
    groups_batched, n_batched, _ = concurrent_mode.find_duplicates(
        tmp_path, workers=4, batch_size=7
    )
    groups_tiny, n_tiny, _ = concurrent_mode.find_duplicates(tmp_path, workers=4, batch_size=1)

    assert n_full == n_batched == n_tiny
    assert _as_sets(groups_full) == _as_sets(groups_batched) == _as_sets(groups_tiny)


def test_parallel_mode_batching_matches_unbatched(tmp_path):
    generate_dataset(tmp_path, count=30, dup_ratio=0.3, min_size=200, max_size=5_000, seed=22)

    groups_full, n_full, _ = parallel_mode.find_duplicates(tmp_path, workers=2, batch_size=None)
    groups_batched, n_batched, _ = parallel_mode.find_duplicates(tmp_path, workers=2, batch_size=5)

    assert n_full == n_batched
    assert _as_sets(groups_full) == _as_sets(groups_batched)


def test_final_batching_matches_unbatched(tmp_path):
    generate_dataset(tmp_path, count=50, dup_ratio=0.3, min_size=200, max_size=5_000, seed=23)

    groups_full, n_full, hits_full, *_ = final.find_duplicates(
        tmp_path, workers=2, threshold=2_000, cache={}, batch_size=None
    )
    groups_batched, n_batched, hits_batched, *_ = final.find_duplicates(
        tmp_path, workers=2, threshold=2_000, cache={}, batch_size=4
    )

    assert n_full == n_batched
    assert hits_full == hits_batched == 0
    assert _as_sets(groups_full) == _as_sets(groups_batched)


def test_final_batching_with_warm_cache_matches_unbatched(tmp_path):
    generate_dataset(tmp_path, count=50, dup_ratio=0.3, min_size=200, max_size=5_000, seed=24)

    cache = {}
    final.find_duplicates(tmp_path, workers=2, threshold=2_000, cache=cache, batch_size=None)
    _groups, n, hits, n_threads, n_processes = final.find_duplicates(
        tmp_path, workers=2, threshold=2_000, cache=cache, batch_size=3
    )

    assert n == 50
    assert n_threads == 0
    assert n_processes == 0
    assert hits > 0
