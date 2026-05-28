"""Integration tests for Heuristic Recovery (rosclaw.how) module."""

import pytest

from rosclaw.how.engine import HeuristicEngine
from rosclaw.how.rules import RuleManager
from rosclaw.how.recovery import RecoveryFormatter, format_recovery_suggestion
from rosclaw.memory.seekdb_client import SeekDBMemoryClient


class TestHeuristicEngine:
    """Tests for HeuristicEngine core functionality."""

    @pytest.fixture
    def engine(self):
        client = SeekDBMemoryClient()
        client.connect()
        return HeuristicEngine(seekdb_client=client)

    @pytest.mark.asyncio
    async def test_seed_defaults(self, engine):
        count = await engine.seed_defaults()
        assert count > 0
        assert engine._cache_valid
        assert len(engine._rule_cache) > 0

    @pytest.mark.asyncio
    async def test_suggest_recovery_exact_match(self, engine):
        await engine.seed_defaults()
        recovery = await engine.suggest_recovery("joint limit exceeded")
        assert recovery is not None
        assert recovery["source"] == "heuristic"

    @pytest.mark.asyncio
    async def test_suggest_recovery_substring_match(self, engine):
        await engine.seed_defaults()
        recovery = await engine.suggest_recovery("ERROR: joint limit exceeded on axis 3")
        assert recovery is not None
        assert recovery["source"] == "heuristic"

    @pytest.mark.asyncio
    async def test_suggest_recovery_no_match(self, engine):
        await engine.seed_defaults()
        recovery = await engine.suggest_recovery("completely unknown magical unicorn failure")
        assert recovery is None

    @pytest.mark.asyncio
    async def test_record_outcome(self, engine):
        await engine.seed_defaults()
        rule_id = list(engine._rule_cache.keys())[0]
        ok = await engine.record_outcome(rule_id, success=True)
        assert ok is True
        rule = engine._rule_cache[rule_id]
        assert rule["success_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_stats(self, engine):
        await engine.seed_defaults()
        stats = engine.get_stats()
        assert stats["rule_count"] > 0
        assert stats["cache_valid"] is True

    @pytest.mark.asyncio
    async def test_suggest_recovery_joint_overload(self, engine):
        await engine.seed_defaults()
        recovery = await engine.suggest_recovery("joint overload detected on axis 2")
        assert recovery is not None
        assert "payload" in recovery["action"].lower()
        assert recovery["source"] == "heuristic"

    @pytest.mark.asyncio
    async def test_suggest_recovery_collision_avoidance(self, engine):
        await engine.seed_defaults()
        recovery = await engine.suggest_recovery("collision avoidance triggered near workspace boundary")
        assert recovery is not None
        assert "compliant" in recovery["action"].lower()
        assert recovery["source"] == "heuristic"

    @pytest.mark.asyncio
    async def test_suggest_recovery_communication_timeout(self, engine):
        await engine.seed_defaults()
        recovery = await engine.suggest_recovery("communication timeout to ROS master")
        assert recovery is not None
        assert "backoff" in recovery["action"].lower()
        assert recovery["source"] == "heuristic"


class TestRuleManager:
    """Tests for RuleManager CRUD operations."""

    @pytest.fixture
    def manager(self):
        client = SeekDBMemoryClient()
        client.connect()
        return RuleManager(client)

    def test_add_and_get_rule(self, manager):
        rid = manager.add_rule("test_001", "test condition", "test action", priority=5)
        rule = manager.get_rule(rid)
        assert rule is not None
        assert rule["condition"] == "test condition"
        assert rule["priority"] == 5

    def test_update_rule(self, manager):
        rid = manager.add_rule("test_002", "old condition", "old action")
        ok = manager.update_rule(rid, action="new action", priority=3)
        assert ok is True
        rule = manager.get_rule(rid)
        assert rule["action"] == "new action"

    def test_list_rules_filters_negative(self, manager):
        rid = manager.add_rule("test_del", "to delete", "action")
        manager.delete_rule(rid)
        rules = manager.list_rules()
        ids = [r["id"] for r in rules]
        assert rid not in ids


class TestRecoveryFormatter:
    """Tests for RecoveryFormatter utilities."""

    def test_to_event_payload(self):
        rule = {
            "rule_id": "r1", "condition": "collision", "action": "replan",
            "priority": 2, "source": "heuristic", "success_count": 3, "failure_count": 1,
        }
        payload = RecoveryFormatter.to_event_payload(rule, request_id="req42")
        assert payload["request_id"] == "req42"
        assert payload["suggestion"] == "replan"

    def test_apply_trajectory_reduce_velocity(self):
        traj = [[1.0, 2.0], [3.0, 4.0]]
        result = RecoveryFormatter.apply_trajectory_adjustment(traj, "Reduce velocity by 50%")
        assert result == [[0.5, 1.0], [1.5, 2.0]]

    def test_format_recovery_suggestion(self):
        recovery = {"action": "clamp torque", "source": "heuristic"}
        text = format_recovery_suggestion(recovery)
        assert "clamp torque" in text

    def test_format_recovery_suggestion_none(self):
        text = format_recovery_suggestion(None)
        assert "No heuristic" in text


class TestMCPHeuristicTool:
    """Tests for MCP get_recovery_strategy tool."""

    @pytest.mark.asyncio
    async def test_mcp_tool_registered(self):
        from rosclaw.agent_runtime.mcp_hub import MCPHub
        from rosclaw.core.event_bus import EventBus

        event_bus = EventBus()
        hub = MCPHub(event_bus=event_bus, robot_id="ur5e")
        hub._do_initialize()
        hub._register_get_recovery_strategy_tool()

        tool_names = [t["name"] for t in hub.tools]
        assert "get_recovery_strategy" in tool_names
        hub._do_stop()

    @pytest.mark.asyncio
    async def test_mcp_handle_get_recovery_strategy(self):
        from rosclaw.agent_runtime.mcp_hub import MCPHub
        from rosclaw.core.event_bus import EventBus

        event_bus = EventBus()
        hub = MCPHub(event_bus=event_bus, robot_id="ur5e")
        hub._register_get_recovery_strategy_tool()

        class MockRuntime:
            def __init__(self):
                client = SeekDBMemoryClient()
                client.connect()
                self.how = HeuristicEngine(seekdb_client=client)

        hub.runtime = MockRuntime()
        await hub.runtime.how.seed_defaults()

        result = await hub.handle_tool_call(
            "get_recovery_strategy", {"error_log": "joint limit exceeded"}
        )

        assert result["status"] == "ok"
        assert result["matched"] is True
        assert "action" in result

    @pytest.mark.asyncio
    async def test_mcp_handle_get_recovery_strategy_no_match(self):
        from rosclaw.agent_runtime.mcp_hub import MCPHub
        from rosclaw.core.event_bus import EventBus

        event_bus = EventBus()
        hub = MCPHub(event_bus=event_bus, robot_id="ur5e")
        hub._register_get_recovery_strategy_tool()

        class MockRuntime:
            def __init__(self):
                client = SeekDBMemoryClient()
                client.connect()
                self.how = HeuristicEngine(seekdb_client=client)

        hub.runtime = MockRuntime()
        await hub.runtime.how.seed_defaults()

        result = await hub.handle_tool_call(
            "get_recovery_strategy", {"error_log": "unicorn magic failure unknown"}
        )

        assert result["status"] == "ok"
        assert result["matched"] is False
