import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dupfinder import generator
from dupfinder.generator import generate_dataset


def test_generate_dataset_creates_expected_file_count(tmp_path):
    generate_dataset(tmp_path, count=20, dup_ratio=0.3, min_size=100, max_size=100, seed=42)

    files = list(tmp_path.glob("*.bin"))
    assert len(files) == 20


def test_generate_dataset_produces_duplicates(tmp_path):
    generate_dataset(tmp_path, count=10, dup_ratio=0.5, min_size=200, max_size=200, seed=1)

    contents = [f.read_bytes() for f in tmp_path.glob("*.bin")]
    assert len(set(contents)) < len(contents)


def test_generate_dataset_rejects_invalid_dup_ratio(tmp_path):
    with pytest.raises(ValueError):
        generate_dataset(tmp_path, count=5, dup_ratio=1.0, min_size=10, max_size=10)


def test_generate_dataset_rejects_invalid_sizes(tmp_path):
    with pytest.raises(ValueError):
        generate_dataset(tmp_path, count=5, dup_ratio=0.2, min_size=100, max_size=10)


def test_generate_dataset_rejects_invalid_count(tmp_path):
    with pytest.raises(ValueError):
        generate_dataset(tmp_path, count=0, dup_ratio=0.1, min_size=10, max_size=10)


def test_parse_args_defaults():
    args = generator._parse_args(["--out", "d", "--count", "5"])

    assert args.out == "d"
    assert args.count == 5
    assert args.dup_ratio == 0.1
    assert args.min_size == 1024
    assert args.max_size == 1024
    assert args.seed is None


def test_main_generates_dataset_and_prints_summary(tmp_path, capsys):
    out_dir = tmp_path / "out"

    generator.main(
        [
            "--out",
            str(out_dir),
            "--count",
            "7",
            "--dup-ratio",
            "0.0",
            "--min-size",
            "50",
            "--max-size",
            "50",
        ]
    )

    assert len(list(out_dir.glob("*.bin"))) == 7
    assert "Generados 7 archivos" in capsys.readouterr().out
