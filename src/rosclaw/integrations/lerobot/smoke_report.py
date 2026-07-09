"""Smoke report persistence for the LeRobot bridge.

Reports are written to ``~/.rosclaw/lerobot/smoke_reports/`` and are used by
``rosclaw lerobot doctor`` to distinguish "available" from "validated"
capabilities.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rosclaw.firstboot.workspace import get_rosclaw_home


SMOKE_REPORT_SCHEMA_VERSION = "rosclaw.lerobot.smoke.v1"
DEFAULT_REPORT_SUBDIR = "lerobot/smoke_reports"


@dataclass
class SmokeReport:
    """A single real-policy smoke report."""

    schema_version: str = SMOKE_REPORT_SCHEMA_VERSION
    created_at: str = ""
    policy: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)
    stages: dict[str, str] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    action_proposal: dict[str, Any] | None = None
    timing: dict[str, float] = field(default_factory=dict)
    status: str = "error"
    error: dict[str, Any] | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "policy": self.policy,
            "runtime": self.runtime,
            "stages": self.stages,
            "features": self.features,
            "action_proposal": self.action_proposal,
            "timing": self.timing,
            "status": self.status,
        }
        if self.error is not None:
            out["error"] = self.error
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SmokeReport":
        return cls(
            schema_version=data.get("schema_version", SMOKE_REPORT_SCHEMA_VERSION),
            created_at=data.get("created_at", ""),
            policy=data.get("policy", {}),
            runtime=data.get("runtime", {}),
            stages=data.get("stages", {}),
            features=data.get("features", {}),
            action_proposal=data.get("action_proposal"),
            timing=data.get("timing", {}),
            status=data.get("status", "error"),
            error=data.get("error"),
        )


def get_smoke_report_dir() -> Path:
    """Return the directory where smoke reports are stored."""
    return get_rosclaw_home() / DEFAULT_REPORT_SUBDIR


def write_smoke_report(report: SmokeReport, *, suffix: str = "") -> Path:
    """Write a smoke report JSON and a ``latest.json`` symlink/overwrite."""
    report_dir = get_smoke_report_dir()
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", report.policy.get("repo_id", "unknown"))
    filename = f"{timestamp}_{safe_name}.json"
    if suffix:
        filename = f"{timestamp}_{safe_name}_{suffix}.json"

    path = report_dir / filename
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    latest_link = report_dir / "latest.json"
    try:
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(path.name)
    except OSError:
        # Fallback: write a small redirect file if symlinks are not supported.
        latest_link.write_text(json.dumps({"latest_report": path.name}, indent=2), encoding="utf-8")

    return path


def read_latest_smoke_report() -> SmokeReport | None:
    """Return the most recent smoke report, or None if none exists."""
    report_dir = get_smoke_report_dir()
    latest_link = report_dir / "latest.json"
    if latest_link.is_symlink():
        target = latest_link.resolve()
        if target.exists():
            return _read_report_file(target)
        return None

    if latest_link.exists():
        try:
            redirect = json.loads(latest_link.read_text(encoding="utf-8"))
            target = report_dir / redirect.get("latest_report", "")
            if target.exists():
                return _read_report_file(target)
        except Exception:  # noqa: BLE001
            pass

    # Fallback: find the most recent report by filename.
    reports = sorted(report_dir.glob("*.json"), reverse=True)
    for candidate in reports:
        if candidate.name != "latest.json":
            return _read_report_file(candidate)
    return None


def _read_report_file(path: Path) -> SmokeReport | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return SmokeReport.from_dict(data)
    except Exception:  # noqa: BLE001
        return None


def get_validation_status() -> dict[str, Any]:
    """Return a summary of the latest smoke validation for doctor output."""
    report = read_latest_smoke_report()
    if report is None:
        return {
            "validated": False,
            "last_policy": None,
            "last_status": None,
            "action_shape": None,
            "time": None,
        }
    return {
        "validated": report.status == "ok",
        "last_policy": report.policy.get("repo_id") or report.policy.get("local_path"),
        "last_status": report.status,
        "action_shape": report.action_proposal.get("shape") if report.action_proposal else None,
        "time": report.created_at,
    }
