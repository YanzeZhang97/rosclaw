"""
ROSClaw MCP Hub - LLM Interface

Provides MCP (Model Context Protocol) server that exposes
robot control tools to LLMs. This is the primary interface
between AI agents and the physical world.

The MCP Hub:
1. Registers tools for robot control (move, grasp, etc.)
2. Maintains AgentContext with grounding information
3. Validates all commands through the Digital Twin Firewall
4. Publishes events to the EventBus for module coordination
5. Uses command-response pattern (NOT fire-and-forget)
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from rosclaw.core.event_bus import EventBus, Event, EventPriority
from rosclaw.core.lifecycle import LifecycleMixin


@dataclass
class AgentContext:
    """
    Context maintained for an LLM agent session.

    This provides the "grounding" - the physical understanding
    that allows the LLM to reason about the robot and world.
    """
    session_id: str
    robot_id: str
    current_task: Optional[str] = None
    task_history: list[dict] = field(default_factory=list)
    robot_model_description: str = ""
    current_joint_positions: list[float] = field(default_factory=list)
    current_end_effector_pose: Optional[list[float]] = None
    active_skills: list[str] = field(default_factory=list)
    safety_level: str = "strict"

    def to_mcp_context(self) -> dict:
        """Convert to MCP context format for LLM."""
        return {
            "session_id": self.session_id,
            "robot": {
                "id": self.robot_id,
                "description": self.robot_model_description,
                "current_state": {
                    "joint_positions": self.current_joint_positions,
                    "end_effector_pose": self.current_end_effector_pose,
                },
            },
            "current_task": self.current_task,
            "active_skills": self.active_skills,
            "safety_level": self.safety_level,
        }


class MCPHub(LifecycleMixin):
    """
    MCP Server Hub for ROSClaw.

    Exposes robot control capabilities to LLMs through the
    Model Context Protocol. All tool calls are validated
    and routed through the EventBus using command-response pattern.
    """

    def __init__(self, event_bus: EventBus, robot_id: str = "rosclaw_default"):
        super().__init__()
        self.event_bus = event_bus
        self.robot_id = robot_id
        self.context = AgentContext(
            session_id="default",
            robot_id=robot_id,
        )
        self._tools: dict[str, dict] = {}
        self._server: Optional[Any] = None
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._default_timeout: float = 30.0

    def _do_initialize(self) -> None:
        """Initialize MCP server and register tools."""
        try:
            from mcp.server import Server
            self._server = Server("rosclaw-mcp")
            self._register_all_tools()
            print("[MCPHub] MCP server initialized")
        except ImportError:
            print("[MCPHub] MCP library not available, running in mock mode")
            self._server = None

        # Subscribe to robot state updates
        self.event_bus.subscribe("robot.joint_states", self._on_joint_states)
        self.event_bus.subscribe("robot.end_effector_pose", self._on_end_effector_pose)
        # Subscribe to command responses
        self.event_bus.subscribe("agent.response", self._on_agent_response)

    def _do_start(self) -> None:
        """Start the MCP server."""
        print("[MCPHub] MCP Hub started")

    def _do_stop(self) -> None:
        """Stop the MCP server."""
        print("[MCPHub] MCP Hub stopped")
        # Cancel any pending futures
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.cancel()
        self._pending_requests.clear()

    def _register_all_tools(self) -> None:
        """Register all robot control tools."""
        self._register_move_tool()
        self._register_grasp_tool()
        self._register_get_state_tool()
        self._register_validate_trajectory_tool()
        self._register_emergency_stop_tool()

    def _register_move_tool(self) -> None:
        """Register move_joints tool."""
        self._tools["move_joints"] = {
            "name": "move_joints",
            "description": "Move robot joints to target positions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "joint_positions": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Target joint positions in radians",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Movement duration in seconds",
                        "default": 2.0,
                    },
                },
                "required": ["joint_positions"],
            },
        }

    def _register_grasp_tool(self) -> None:
        """Register grasp tool."""
        self._tools["grasp"] = {
            "name": "grasp",
            "description": "Control the gripper to grasp or release",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["close", "open"],
                        "description": "Grasp action",
                    },
                    "force": {
                        "type": "number",
                        "description": "Grasp force (0-1)",
                        "default": 0.5,
                    },
                },
                "required": ["action"],
            },
        }

    def _register_get_state_tool(self) -> None:
        """Register get_robot_state tool."""
        self._tools["get_robot_state"] = {
            "name": "get_robot_state",
            "description": "Get current robot joint positions and state",
            "inputSchema": {"type": "object", "properties": {}},
        }

    def _register_validate_trajectory_tool(self) -> None:
        """Register validate_trajectory tool."""
        self._tools["validate_trajectory"] = {
            "name": "validate_trajectory",
            "description": "Validate a trajectory through Digital Twin before execution",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "List of joint position waypoints",
                    },
                },
                "required": ["waypoints"],
            },
        }

    def _register_emergency_stop_tool(self) -> None:
        """Register emergency_stop tool."""
        self._tools["emergency_stop"] = {
            "name": "emergency_stop",
            "description": "EMERGENCY STOP - halt all robot motion immediately",
            "inputSchema": {"type": "object", "properties": {}},
        }

    async def handle_tool_call(self, name: str, arguments: dict) -> dict:
        """
        Handle an MCP tool call from an LLM.

        All tool calls are converted to EventBus events using
        command-response pattern for reliable execution feedback.
        """
        print(f"[MCPHub] Tool call: {name}({arguments})")

        if name == "move_joints":
            return await self._handle_move_joints(arguments)
        elif name == "grasp":
            return await self._handle_grasp(arguments)
        elif name == "get_robot_state":
            return self._handle_get_state()
        elif name == "validate_trajectory":
            return await self._handle_validate_trajectory(arguments)
        elif name == "emergency_stop":
            return self._handle_emergency_stop()
        else:
            return {"error": f"Unknown tool: {name}"}

    async def _send_command_and_wait(
        self,
        topic: str,
        payload: dict,
        timeout: Optional[float] = None,
    ) -> dict:
        """
        Send a command via EventBus and wait for response.

        Uses request-response pattern:
        1. Generate unique request_id
        2. Create asyncio.Future
        3. Publish command with request_id in metadata
        4. Await response future with timeout
        5. Return execution result
        """
        request_id = str(uuid.uuid4())[:8]
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        event = Event(
            topic=topic,
            payload=payload,
            source="mcp_hub",
            priority=EventPriority.HIGH,
            metadata={"request_id": request_id},
        )
        self.event_bus.publish(event)

        try:
            result = await asyncio.wait_for(future, timeout=timeout or self._default_timeout)
            return result
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "message": f"Command timed out after {timeout or self._default_timeout}s",
                "request_id": request_id,
            }
        finally:
            self._pending_requests.pop(request_id, None)

    def _on_agent_response(self, event: Event) -> None:
        """Handle command responses from other modules."""
        request_id = event.metadata.get("request_id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(event.payload)

    async def _handle_move_joints(self, arguments: dict) -> dict:
        """Handle move_joints tool call with command-response."""
        positions = arguments.get("joint_positions", [])
        duration = arguments.get("duration", 2.0)

        result = await self._send_command_and_wait(
            topic="agent.command",
            payload={
                "action": "move_joints",
                "joint_positions": positions,
                "duration": duration,
            },
        )

        # If timeout or no response handler, fall back to issued status
        if result.get("status") == "timeout":
            return {
                "status": "command_issued",
                "action": "move_joints",
                "target_positions": positions,
                "warning": "No response received from execution layer",
            }
        return result

    async def _handle_grasp(self, arguments: dict) -> dict:
        """Handle grasp tool call with command-response."""
        action = arguments.get("action", "close")
        force = arguments.get("force", 0.5)

        result = await self._send_command_and_wait(
            topic="agent.command",
            payload={
                "action": "grasp",
                "grasp_action": action,
                "force": force,
            },
        )

        if result.get("status") == "timeout":
            return {
                "status": "command_issued",
                "action": f"grasp_{action}",
                "warning": "No response received from execution layer",
            }
        return result

    def _handle_get_state(self) -> dict:
        """Handle get_robot_state tool call."""
        return {
            "status": "ok",
            "robot_state": {
                "joint_positions": self.context.current_joint_positions,
                "end_effector_pose": self.context.current_end_effector_pose,
            },
        }

    async def _handle_validate_trajectory(self, arguments: dict) -> dict:
        """Handle validate_trajectory tool call with command-response."""
        waypoints = arguments.get("waypoints", [])

        result = await self._send_command_and_wait(
            topic="agent.command",
            payload={
                "action": "validate_trajectory",
                "waypoints": waypoints,
            },
        )

        if result.get("status") == "timeout":
            return {
                "status": "validation_requested",
                "waypoints_count": len(waypoints),
                "warning": "No response received from validation layer",
            }
        return result

    def _handle_emergency_stop(self) -> dict:
        """Handle emergency_stop tool call."""
        self.event_bus.publish(Event(
            topic="robot.emergency_stop",
            payload={"reason": "LLM emergency stop command"},
            source="mcp_hub",
            priority=EventPriority.CRITICAL,
        ))
        return {"status": "emergency_stop_triggered"}

    def _on_joint_states(self, event: Event) -> None:
        """Update context with joint state."""
        payload = event.payload
        if isinstance(payload, dict) and "positions" in payload:
            self.context.current_joint_positions = payload["positions"]

    def _on_end_effector_pose(self, event: Event) -> None:
        """Update context with end effector pose."""
        self.context.current_end_effector_pose = event.payload

    def update_robot_description(self, description: str) -> None:
        """Update robot model description in context."""
        self.context.robot_model_description = description

    @property
    def tools(self) -> list[dict]:
        """Get list of available tools."""
        return list(self._tools.values())
