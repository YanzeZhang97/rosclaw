"""Telemetry configuration generation for ROSClaw First Boot."""

from __future__ import annotations

from pathlib import Path

import yaml


def generate_telemetry_yaml(home: Path, enabled: bool = False) -> Path:
    """Generate telemetry.yaml with everything disabled by default."""
    path = home / "config" / "telemetry.yaml"
    config = {
        "schema_version": "1.0",
        "telemetry": {
            "enabled": enabled,
            "anonymous_install_ping": enabled,
            "anonymous_doctor_ping": False,
            "endpoint": "https://api.rosclaw.io/v1/telemetry",
        },
        "privacy": {
            "send_install_id": True,
            "send_os": True,
            "send_arch": True,
            "send_python_version": True,
            "send_error_code": True,
            "send_hostname": False,
            "send_username": False,
            "send_ip": False,
            "send_workspace_path": False,
            "send_logs": False,
        },
    }
    path.write_text(
        yaml.safe_dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def build_install_ping_payload(
    install_state: dict,
    status: str = "success",
    error_code: str | None = None,
    duration_ms: int | None = None,
) -> dict:
    """Build an anonymous install ping payload.

    This only includes non-identifying fields: hashed install_id, platform,
    Python version, install backend/channel, and result status.
    """
    import hashlib

    install_id = install_state.get("install_id", "")
    install_id_hash = hashlib.sha256(install_id.encode("utf-8")).hexdigest()
    platform = install_state.get("platform", {})
    python = install_state.get("python", {})

    return {
        "event": "install_completed",
        "schema_version": "1.0",
        "anonymous": True,
        "install_id_hash": f"sha256:{install_id_hash}",
        "timestamp": install_state.get("installed_at"),
        "rosclaw_version": install_state.get("rosclaw_version", "unknown"),
        "installer_version": install_state.get("installer_version", "1.0.0"),
        "platform": {
            "os": platform.get("os"),
            "arch": platform.get("arch"),
            "is_wsl": platform.get("is_wsl", False),
        },
        "python": {
            "major": python.get("version", "").split(".")[0] if python.get("version") else None,
            "minor": python.get("version", "").split(".")[1] if python.get("version") else None,
        },
        "install_backend": install_state.get("install_backend"),
        "install_channel": install_state.get("install_channel"),
        "result": {
            "status": status,
            "error_code": error_code,
            "duration_ms": duration_ms,
        },
    }
