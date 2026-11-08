import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder.generator import generate_dataset
from dupfinder.modes import baseline, structural


def _as_sets(groups):
    return {frozenset(g) for g in groups}


def test_matches_baseline(tmp_path):
    generate_dataset(tmp_path, count=60, dup_ratio=0.2, min_size=200, max_size=50_000, seed=5)

    base_groups, base_n = baseline.find_duplicates(tmp_path)
    struct_groups, struct_n, _ = structural.find_duplicates(tmp_path)

    assert struct_n == base_n
    assert _as_sets(struct_groups) == _as_sets(base_groups)


def test_prefilter_skips_unique_sizes(tmp_path):
    generate_dataset(tmp_path, count=60, dup_ratio=0.2, min_size=200, max_size=50_000, seed=5)

    _, n, n_hashed = structural.find_duplicates(tmp_path)

    assert n_hashed < n


def test_hash_file_matches_known_digest(tmp_path):
    sample = tmp_path / "f.bin"
    sample.write_bytes(b"hola mundo")

    assert structural.hash_file(sample) == hashlib.sha256(b"hola mundo").hexdigest()


def test_hash_file_chunked_matches_full_read(tmp_path):
    sample = tmp_path / "big.bin"
    content = bytes(range(256)) * 1000
    sample.write_bytes(content)

    assert structural.hash_file(sample, chunk_size=1024) == hashlib.sha256(content).hexdigest()


def test_no_duplicates(tmp_path):
    generate_dataset(tmp_path, count=6, dup_ratio=0.0, min_size=128, max_size=512, seed=2)

    groups, n, _ = structural.find_duplicates(tmp_path)

    assert n == 6
    assert groups == []


def test_empty_directory(tmp_path):
    groups, n, n_hashed = structural.find_duplicates(tmp_path)

    assert n == 0
    assert n_hashed == 0
    assert groups == []


def test_run_prints_report(tmp_path, capsys):
    generate_dataset(tmp_path, count=10, dup_ratio=0.2, min_size=100, max_size=100, seed=5)

    structural.run(tmp_path, workers=1, threshold=0)

    out = capsys.readouterr().out
    assert "modo=estructura" in out
    assert "archivos hasheados" in out


def test_run_rejects_nonexistent_path(tmp_path):
    with pytest.raises(SystemExit):
        structural.run(tmp_path / "no_existe", workers=1, threshold=0)
