"""Tests for Agent Runtime."""

import pytest

from rosclaw.core.event_bus import EventBus, Event, EventPriority
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


async def test_mcp_hub_handle_move_joints_timeout():
    """Test move_joints falls back to command_issued when no response."""
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    # No response handler registered, so it should timeout and fallback
    result = await hub.handle_tool_call("move_joints", {"joint_positions": [0.1] * 6, "duration": 1.0})
    assert result["status"] == "command_issued"
    assert result["action"] == "move_joints"
    hub.stop()


async def test_mcp_hub_handle_move_joints_with_response():
    """Test move_joints receives response from execution layer."""
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()

    # Register a mock execution layer that responds
    def mock_executor(event):
        request_id = event.metadata.get("request_id")
        if request_id and event.payload.get("action") == "move_joints":
            bus.publish(Event(
                topic="agent.response",
                payload={
                    "status": "success",
                    "action": "move_joints",
                    "final_positions": event.payload["joint_positions"],
                },
                source="mock_executor",
                metadata={"request_id": request_id},
            ))

    bus.subscribe("agent.command", mock_executor)

    result = await hub.handle_tool_call("move_joints", {"joint_positions": [0.1] * 6, "duration": 1.0})
    assert result["status"] == "success"
    assert result["action"] == "move_joints"
    hub.stop()


async def test_mcp_hub_handle_grasp():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    result = await hub.handle_tool_call("grasp", {"action": "close", "force": 0.8})
    assert result["status"] == "command_issued"
    hub.stop()


async def test_mcp_hub_handle_emergency_stop():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    result = await hub.handle_tool_call("emergency_stop", {})
    assert result["status"] == "emergency_stop_triggered"
    hub.stop()


async def test_mcp_hub_unknown_tool():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    result = await hub.handle_tool_call("nonexistent", {})
    assert "error" in result
    hub.stop()


def test_mcp_hub_context_update():
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()
    hub.update_robot_description("UR5e robot arm")
    assert hub.context.robot_model_description == "UR5e robot arm"
    hub.stop()


async def test_mcp_hub_command_response_pattern():
    """Test the full command-response pattern with request_id matching."""
    bus = EventBus()
    hub = MCPHub(bus, robot_id="test")
    hub.initialize()

    received_requests = []

    def mock_handler(event):
        received_requests.append(event.metadata.get("request_id"))
        request_id = event.metadata.get("request_id")
        # Simulate async processing
        bus.publish(Event(
            topic="agent.response",
            payload={"status": "completed", "request_id": request_id},
            source="mock",
            metadata={"request_id": request_id},
        ))

    bus.subscribe("agent.command", mock_handler)

    result = await hub.handle_tool_call("move_joints", {"joint_positions": [0.5] * 6})
    assert result["status"] == "completed"
    assert len(received_requests) == 1
    assert received_requests[0] is not None
    hub.stop()
