"""Tests for Agent Runtime."""

import pytest

from rosclaw.core.event_bus import EventBus
from rosclaw.agent_runtime.mcp_hub import MCPHub, AgentContext


def test_agent_context():
    ctx = AgentContext(session_id="sess_1", robot_id="ur5e_001")
    ctx.current_joint_positions = [0.1] * 6
    mcp = ctx.to_mcp_context()
    assert mcp["session_id"] == "sess_1"
    assert mcp["robot"]["id"] == "ur5e_001"
    assert len(mcp["robot"]["current_state"]["joint_positions"]) == 6


def test_mcp_hub_tools():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    tools = hub.tools
    assert len(tools) == 5
    names = [t["name"] for t in tools]
    assert "move_joints" in names
    assert "grasp" in names
    assert "emergency_stop" in names
    hub.stop()


def test_mcp_hub_handle_move_joints():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    result = hub.handle_tool_call("move_joints", {"joint_positions": [0.1] * 6, "duration": 1.0})
    assert result["status"] == "command_issued"
    hub.stop()


def test_mcp_hub_handle_emergency_stop():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    result = hub.handle_tool_call("emergency_stop", {})
    assert result["status"] == "emergency_stop_triggered"
    hub.stop()


def test_mcp_hub_unknown_tool():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    result = hub.handle_tool_call("nonexistent", {})
    assert "error" in result
    hub.stop()


def test_mcp_hub_context_update():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    hub.update_robot_description("UR5e robot arm")
    assert hub.context.robot_model_description == "UR5e robot arm"
    hub.stop()
