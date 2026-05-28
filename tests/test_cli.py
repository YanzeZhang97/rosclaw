"""Tests for rosclaw.cli"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestVersion:
    def test_version_flag(self, capsys):
        from rosclaw.cli import main

        with pytest.raises(SystemExit) as exc:
            sys.argv = ["rosclaw", "--version"]
            main()
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "rosclaw 1.0.0" in captured.out


class TestInit:
    def test_init_creates_workspace(self, tmp_path):
        from rosclaw.cli import main

        ws = tmp_path / "ws"
        sys.argv = ["rosclaw", "init", str(ws)]
        assert main() == 0

        assert (ws / "rosclaw.yaml").exists()
        assert (ws / "practice_data").is_dir()
        assert (ws / "skills").is_dir()
        assert (ws / "models").is_dir()

        config = (ws / "rosclaw.yaml").read_text()
        assert "robot_id: rosclaw_bot" in config
        assert "safety_level: MODERATE" in config

    def test_init_refuses_overwrite(self, tmp_path):
        from rosclaw.cli import main

        ws = tmp_path / "ws"
        sys.argv = ["rosclaw", "init", str(ws)]
        main()

        sys.argv = ["rosclaw", "init", str(ws)]
        assert main() == 1

    def test_init_force_overwrite(self, tmp_path):
        from rosclaw.cli import main

        ws = tmp_path / "ws"
        sys.argv = ["rosclaw", "init", str(ws)]
        main()

        sys.argv = ["rosclaw", "init", "--force", str(ws)]
        assert main() == 0


class TestRun:
    @patch("rosclaw.core.Runtime")
    def test_run_starts_runtime(self, mock_runtime_cls):
        from rosclaw.cli import main

        mock_runtime = MagicMock()
        mock_runtime.is_running = True
        mock_runtime_cls.return_value = mock_runtime

        call_count = 0

        def fake_sleep(t):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                mock_runtime.is_running = False

        with patch("time.sleep", fake_sleep):
            sys.argv = ["rosclaw", "run", "--robot-id", "test_bot"]
            assert main() == 0

        mock_runtime.initialize.assert_called_once()
        mock_runtime.start.assert_called_once()
        mock_runtime.stop.assert_called_once()


class TestStatus:
    def test_status(self, capsys):
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "status"]
        assert main() == 0
        captured = capsys.readouterr()
        assert "ROSClaw v1.0 Status" in captured.out
        assert "Overall:" in captured.out
        assert "HEALTHY" in captured.out

    def test_status_shows_modules(self, capsys):
        from rosclaw.cli import main

        sys.argv = ["rosclaw", "status"]
        main()
        captured = capsys.readouterr()
        assert "core.runtime" in captured.out
        assert "firewall.validator" in captured.out
        assert "memory.interface" in captured.out
