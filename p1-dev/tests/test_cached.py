import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.generator import generate_dataset
from dupfinder.modes import cached, structural


def _as_sets(groups):
    return {frozenset(g) for g in groups}


def test_matches_structural_with_empty_cache(tmp_path):
    generate_dataset(tmp_path, count=40, dup_ratio=0.25, min_size=200, max_size=20_000, seed=11)

    struct_groups, struct_n, _ = structural.find_duplicates(tmp_path)
    cached_groups, cached_n, hits, misses = cached.find_duplicates(tmp_path, cache={})

    assert cached_n == struct_n
    assert _as_sets(cached_groups) == _as_sets(struct_groups)
    assert hits == 0
    assert misses > 0


def test_second_scan_reuses_cache_without_changes(tmp_path):
    generate_dataset(tmp_path, count=40, dup_ratio=0.25, min_size=200, max_size=20_000, seed=11)

    cache = {}
    groups1, _, hits1, misses1 = cached.find_duplicates(tmp_path, cache)
    groups2, _, hits2, misses2 = cached.find_duplicates(tmp_path, cache)

    assert hits1 == 0
    assert misses2 == 0
    assert hits2 == misses1
    assert _as_sets(groups1) == _as_sets(groups2)


def test_invalidates_when_file_changes(tmp_path):
    generate_dataset(tmp_path, count=10, dup_ratio=0.0, min_size=100, max_size=100, seed=2)
    target = sorted(tmp_path.glob("*.bin"))[0]

    cache = {}
    cached.find_duplicates(tmp_path, cache)
    _, _, hits_before, misses_before = cached.find_duplicates(tmp_path, cache)
    assert misses_before == 0
    assert hits_before == 10

    target.write_bytes(b"x" * 100)
    future = time.time() + 5
    os.utime(target, (future, future))

    _, _, hits_after, misses_after = cached.find_duplicates(tmp_path, cache)

    assert misses_after == 1
    assert hits_after == 9


def test_load_cache_missing_file_returns_empty(tmp_path):
    assert cached.load_cache(tmp_path / "nope.json") == {}


def test_save_and_load_cache_roundtrip(tmp_path):
    cache_path = tmp_path / "c.json"
    cached.save_cache(cache_path, {"a": {"size": 1, "mtime": 2.0, "hash": "abc"}})

    assert cached.load_cache(cache_path) == {"a": {"size": 1, "mtime": 2.0, "hash": "abc"}}


def test_default_cache_path_is_sibling_of_scanned_dir(tmp_path):
    scan_dir = tmp_path / "data"
    scan_dir.mkdir()

    cache_path = cached.default_cache_path(scan_dir)

    assert cache_path.parent == tmp_path


def test_run_persists_cache_to_disk(tmp_path):
    generate_dataset(tmp_path, count=20, dup_ratio=0.2, min_size=200, max_size=5000, seed=4)

    cache_path = tmp_path.parent / "run_cache.json"
    cached.run(path=tmp_path, workers=1, threshold=0, cache_file=cache_path)

    assert cache_path.exists()
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    assert len(data) > 0


def test_load_cache_corrupt_json_returns_empty(tmp_path):
    cache_path = tmp_path / "bad.json"
    cache_path.write_text("{esto no es json valido", encoding="utf-8")

    assert cached.load_cache(cache_path) == {}
