from __future__ import annotations

from fastapi.testclient import TestClient

from silabus.api.main import app
from silabus.cli import EXIT_NOT_IMPLEMENTED, main

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_gap_is_declared_but_not_implemented() -> None:
    response = client.post("/gap", json={"role": "backend", "skills": ["Python"]})
    assert response.status_code == 501


def test_cli_signals_unfinished_work() -> None:
    assert main(["eval", "--mode", "full"]) == EXIT_NOT_IMPLEMENTED
