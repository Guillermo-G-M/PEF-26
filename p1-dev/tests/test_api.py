import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient

from dupfinder.api import app
from dupfinder.generator import generate_dataset

client = TestClient(app)


def _as_sets(groups):
    return {frozenset(g) for g in groups}


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scan_matches_cli_invariant(tmp_path):
    generate_dataset(tmp_path, count=40, dup_ratio=0.25, min_size=200, max_size=5_000, seed=31)

    response = client.post(
        "/scan",
        json={"path": str(tmp_path), "workers": 2, "threshold": 2_000, "batch_size": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["files_scanned"] == 40
    assert body["redundant_files"] == int(40 * 0.25)
    assert body["cache_hits"] == 0
    assert body["cache_misses"] == body["hashed_with_threads"] + body["hashed_with_processes"]


def test_scan_second_call_reuses_cache(tmp_path):
    generate_dataset(tmp_path, count=30, dup_ratio=0.2, min_size=200, max_size=5_000, seed=32)
    payload = {"path": str(tmp_path), "workers": 2, "threshold": 2_000}

    first = client.post("/scan", json=payload).json()
    second = client.post("/scan", json=payload).json()

    assert first["cache_misses"] > 0
    assert second["cache_hits"] == first["cache_hits"] + first["cache_misses"]
    assert second["cache_misses"] == 0
    assert _as_sets(first["duplicate_groups"]) == _as_sets(second["duplicate_groups"])


def test_scan_rejects_nonexistent_path(tmp_path):
    response = client.post("/scan", json={"path": str(tmp_path / "no_existe")})

    assert response.status_code == 400


def test_scan_rejects_invalid_workers():
    response = client.post("/scan", json={"path": ".", "workers": 0})

    assert response.status_code == 422
