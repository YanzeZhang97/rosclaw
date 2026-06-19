"""Tests for ROSClaw firstboot command."""

from __future__ import annotations

import json
import sys

import yaml


class TestFirstbootNonInteractive:
    def test_firstboot_offline_default(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--profile", "offline", "--no-telemetry"]
        code = main()
        assert code in (0, 2)

        cfg_path = home / "config" / "rosclaw.yaml"
        assert cfg_path.exists()
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert cfg["cloud"]["enabled"] is False
        assert cfg["telemetry"]["enabled"] is False
        assert cfg["sandbox"]["enabled"] is True
        assert cfg["security"]["require_firewall_for_real_robot"] is True
        assert cfg["runtime"]["robot_id"] == "sim_ur5e"

    def test_firstboot_cloud_opt_in(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--profile", "cloud", "--telemetry"]
        code = main()
        assert code in (0, 2)

        cfg = yaml.safe_load((home / "config" / "rosclaw.yaml").read_text(encoding="utf-8"))
        assert cfg["cloud"]["enabled"] is True
        assert cfg["cloud"]["sync"]["configs"] is True
        assert cfg["telemetry"]["enabled"] is True
        assert cfg["telemetry"]["anonymous_install_ping"] is True

    def test_firstboot_idempotent_preserves_custom_robot(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--profile", "offline", "--no-telemetry"]
        main()

        cfg_path = home / "config" / "rosclaw.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        cfg["runtime"]["robot_id"] = "custom_bot"
        cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

        sys.argv = ["rosclaw", "firstboot", "--yes", "--profile", "offline", "--no-telemetry"]
        main()

        cfg2 = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert cfg2["runtime"]["robot_id"] == "custom_bot"
        backups = list((home / "backups").glob("rosclaw.yaml.*.bak"))
        assert len(backups) >= 1

    def test_firstboot_creates_mcp_json(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--enable-mcp"]
        main()

        mcp_path = home / "config" / "mcp.json"
        assert mcp_path.exists()
        mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert mcp["mcpServers"]["rosclaw"]["command"] == "rosclaw-mcp"
        assert "ROSCLAW_HOME" in mcp["mcpServers"]["rosclaw"]["env"]

    def test_firstboot_custom_workspace_path(self, tmp_path, monkeypatch):
        home = tmp_path / "custom-rc"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes"]
        main()

        assert (home / "config" / "rosclaw.yaml").exists()
        assert (home / "state" / "install.json").exists()

    def test_firstboot_state_install_json(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--profile", "offline"]
        main()

        state = json.loads((home / "state" / "install.json").read_text(encoding="utf-8"))
        assert state["firstboot_completed"] is True
        assert state["firstboot_profile"] == "offline"

    def test_firstboot_disables_mcp(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--disable-mcp"]
        main()

        assert not (home / "config" / "mcp.json").exists()


class TestFirstbootDoctorIntegration:
    def test_firstboot_then_doctor_bootstrap(self, tmp_path, monkeypatch):
        home = tmp_path / ".rosclaw"
        monkeypatch.setenv("ROSCLAW_HOME", str(home))
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "firstboot", "--yes", "--profile", "offline", "--no-telemetry"]
        main()

        sys.argv = ["rosclaw", "doctor", "--bootstrap"]
        code = main()
        assert code in (0, 2)
