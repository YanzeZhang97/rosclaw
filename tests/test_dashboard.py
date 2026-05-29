"""Tests for rosclaw.dashboard module."""

import asyncio

import pytest

from rosclaw.dashboard import DashboardMetrics, DashboardServer


class TestDashboardMetrics:
    def test_init(self):
        m = DashboardMetrics()
        assert m.get_uptime_sec() >= 0
        assert m.snapshot()["uptime_sec"] >= 0

    def test_provider_stats_empty(self):
        m = DashboardMetrics()
        stats = m.get_provider_stats()
        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0

    def test_provider_stats(self):
        m = DashboardMetrics()
        m.record_provider_call("vlm", "vlm.grounding", 120.0, "ok")
        m.record_provider_call("vlm", "vlm.grounding", 200.0, "ok")
        m.record_provider_call("skill", "skill.pick", 500.0, "error")

        stats = m.get_provider_stats()
        assert stats["total"] == 3
        assert stats["success_rate"] == 2 / 3
        assert stats["avg_latency_ms"] == pytest.approx(273.33, abs=0.1)
        assert "vlm" in stats["by_provider"]
        assert stats["by_provider"]["vlm"]["calls"] == 2
        assert stats["by_provider"]["skill"]["errors"] == 1

    def test_sandbox_stats(self):
        m = DashboardMetrics()
        m.record_sandbox_validation("pick", True)
        m.record_sandbox_validation("place", False, ["collision_predicted"])

        stats = m.get_sandbox_stats()
        assert stats["total"] == 2
        assert stats["block_rate"] == 0.5
        assert len(stats["recent_violations"]) == 1

    def test_episode_stats(self):
        m = DashboardMetrics()
        m.record_episode("ep_001", "ur5e", "success", reward=0.95, duration_sec=12.3)
        m.record_episode("ep_002", "ur5e", "failure", reward=0.1, duration_sec=5.0)

        stats = m.get_episode_stats()
        assert stats["total"] == 2
        assert stats["success_rate"] == 0.5
        assert stats["avg_reward"] == pytest.approx(0.525, abs=0.01)
        assert len(stats["recent"]) == 2

    def test_event_counts(self):
        m = DashboardMetrics()
        m.increment_event("provider.call")
        m.increment_event("provider.call")
        m.increment_event("sandbox.block")

        counts = m.get_event_counts()
        assert counts["provider.call"] == 2
        assert counts["sandbox.block"] == 1

    def test_module_health(self):
        m = DashboardMetrics()
        m.set_module_health("runtime", "HEALTHY")
        m.set_module_health("sandbox", "DEGRADED")

        health = m.get_module_health()
        assert health["runtime"] == "HEALTHY"
        assert health["sandbox"] == "DEGRADED"

    def test_snapshot_completeness(self):
        m = DashboardMetrics()
        snapshot = m.snapshot()
        assert "uptime_sec" in snapshot
        assert "module_health" in snapshot
        assert "provider" in snapshot
        assert "sandbox" in snapshot
        assert "episodes" in snapshot
        assert "event_counts" in snapshot

    def test_rolling_window(self):
        m = DashboardMetrics(max_history=3)
        for i in range(5):
            m.record_provider_call("p", "c", float(i), "ok")
        assert len(m._provider_metrics) == 3


class TestDashboardServer:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        metrics = DashboardMetrics()
        server = DashboardServer(metrics, port=9999)

        await server.start()
        assert server._running is True
        assert server._task is not None

        await server.stop()
        assert server._running is False

    @pytest.mark.asyncio
    async def test_snapshot_api(self):
        metrics = DashboardMetrics()
        metrics.set_module_health("runtime", "HEALTHY")
        server = DashboardServer(metrics, port=9999)

        health = server.get_health()
        assert health["status"] == "HEALTHY"
        assert health["modules"]["runtime"] == "HEALTHY"
        assert "uptime_sec" in health

    def test_get_robots(self):
        from unittest.mock import MagicMock

        metrics = DashboardMetrics()
        server = DashboardServer(metrics, port=9999)

        mock_registry = MagicMock()
        mock_profile = MagicMock()
        mock_profile.robot_id = "ur5e"
        mock_profile.name = "UR5e"
        mock_profile.vendor = "Universal Robots"
        mock_profile.embodiment.dof = 6
        mock_profile.capability.capabilities = [{}, {}, {}]

        mock_registry.list_available.return_value = ["ur5e"]
        mock_registry.get.return_value = mock_profile

        robots = server.get_robots(mock_registry)
        assert len(robots) == 1
        assert robots[0]["robot_id"] == "ur5e"
        assert robots[0]["capabilities"] == 3

    @pytest.mark.asyncio
    async def test_broadcast_no_clients(self):
        metrics = DashboardMetrics()
        server = DashboardServer(metrics, port=9999)

        # Should not crash with no clients
        await server._broadcast('{"test": true}')
        assert len(server._clients) == 0

    @pytest.mark.asyncio
    async def test_client_register_unregister(self):
        metrics = DashboardMetrics()
        server = DashboardServer(metrics, port=9999)

        class FakeClient:
            pass

        client = FakeClient()
        server.register_client(client)
        assert client in server._clients

        server.unregister_client(client)
        assert client not in server._clients
