"""Provider CLI contract tests for dry-run physical-AI routing."""

import json
import sys


def _run_cli(monkeypatch, capsys, argv: list[str]) -> tuple[int, dict]:
    from rosclaw.cli import main

    monkeypatch.setattr(sys, "argv", ["rosclaw", *argv])
    code = main()
    captured = capsys.readouterr()
    return code, json.loads(captured.out)


def test_provider_health_json_contract(monkeypatch, capsys):
    code, payload = _run_cli(monkeypatch, capsys, ["provider", "health", "--json"])

    assert code == 0
    assert payload["ok"] is True
    assert payload["provider_count"] >= 8
    assert any(provider["name"] == "vlm" for provider in payload["providers"])


def test_provider_route_explains_vlm_scene_graph(monkeypatch, capsys):
    code, payload = _run_cli(
        monkeypatch,
        capsys,
        ["provider", "route", "--capability", "vlm.scene_graph", "--json"],
    )

    assert code == 0
    assert payload["ok"] is True
    assert payload["selected_provider"] == "vlm"
    assert payload["fallbacks"] == ["world"]
    assert "declares capability" in payload["reason"]
    assert payload["requires_guard"] is True


def test_provider_route_reports_unroutable_capability(monkeypatch, capsys):
    code, payload = _run_cli(
        monkeypatch,
        capsys,
        ["provider", "route", "--capability", "missing.capability", "--json"],
    )

    assert code == 1
    assert payload["ok"] is False
    assert payload["selected_provider"] is None


def test_provider_benchmark_dry_run_json_contract(monkeypatch, capsys):
    code, payload = _run_cli(
        monkeypatch,
        capsys,
        ["provider", "benchmark", "--dry-run", "--json"],
    )

    assert code == 0
    assert payload["dry_run"] is True
    assert payload["status"] == "dry_run"
    assert any(item["capability"] == "vlm.scene_graph" for item in payload["route_plan"])


def test_provider_benchmark_requires_dry_run(monkeypatch, capsys):
    code, payload = _run_cli(monkeypatch, capsys, ["provider", "benchmark", "--json"])

    assert code == 1
    assert payload["ok"] is False
    assert "--dry-run" in payload["error"]
