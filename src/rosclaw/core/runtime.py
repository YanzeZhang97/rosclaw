"""ROSClaw Runtime - Central Orchestrator

The Runtime is the OS kernel of ROSClaw. It:
1. Owns the EventBus (all communication flows through it)
2. Manages all grounding engines (firewall, memory, practice, swarm, skill)
3. Provides the AgentRuntime with a unified interface to the physical world
4. Handles lifecycle coordination across all modules

Architecture:
    Agent Runtime (LLM/MCP)
         |
         v
    ROSClaw Runtime (this file)
    |-- EventBus
    |-- Firewall (Action Grounding)
    |-- Memory (Experience Grounding)
    |-- Practice (Timeline Grounding)
    |-- Swarm (Collaboration Grounding)
    |-- SkillManager (Skill Grounding)
    |-- EURDFParser (Physical Grounding)
    |-- MCPDrivers (Hardware abstraction)
         |
         v
    Physical World (Robot)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from rosclaw.core.event_bus import EventBus, Event, EventPriority
from rosclaw.core.lifecycle import LifecycleMixin, LifecycleState


@dataclass
class RuntimeConfig:
    """Configuration for ROSClaw Runtime."""
    robot_id: str = "rosclaw_default"
    robot_model_path: Optional[str] = None
    enable_firewall: bool = True
    enable_memory: bool = True
    enable_practice: bool = True
    enable_swarm: bool = False
    enable_skill_manager: bool = True
    joint_dof: int = 6
    sampling_rate_hz: int = 1000


class Runtime(LifecycleMixin):
    """
    Central runtime orchestrator for ROSClaw.

    This is the main entry point for the ROSClaw OS. It coordinates
    all grounding engines and provides a unified interface for
    agent runtimes to interact with the physical world.
    """

    def __init__(self, config: Optional[RuntimeConfig] = None):
        super().__init__()
        self.config = config or RuntimeConfig()

        # Core infrastructure
        self.event_bus = EventBus()

        # Grounding engines (initialized on demand)
        self._firewall: Optional[Any] = None
        self._memory: Optional[Any] = None
        self._practice: Optional[Any] = None
        self._swarm: Optional[Any] = None
        self._skill_manager: Optional[Any] = None
        self._e_urdf: Optional[Any] = None
        self._mcp_drivers: dict[str, Any] = {}

        # Internal state
        self._agent_runtime: Optional[Any] = None
        self._modules: list[LifecycleMixin] = []

    def _do_initialize(self) -> None:
        """Initialize all enabled grounding engines."""
        print(f"[Runtime] Initializing ROSClaw Runtime for {self.config.robot_id}")

        # Initialize EventBus subscriptions for internal coordination
        self._setup_internal_subscriptions()

        # Initialize Physical Grounding (e-URDF)
        if self.config.robot_model_path:
            from rosclaw.e_urdf.parser import EURDFParser
            self._e_urdf = EURDFParser(self.config.robot_model_path)
            print(f"[Runtime] Physical Grounding (e-URDF) loaded: {self.config.robot_model_path}")

        # Initialize Action Grounding (Firewall)
        if self.config.enable_firewall and self.config.robot_model_path:
            try:
                from rosclaw.firewall.decorator import DigitalTwinFirewall
                self._firewall = DigitalTwinFirewall(self.config.robot_model_path)
                self._modules.append(self._firewall)
                print("[Runtime] Action Grounding (Firewall) initialized")
            except ImportError:
                print("[Runtime] Firewall module not available (mujoco not installed)")

        # Initialize Experience Grounding (Memory)
        if self.config.enable_memory:
            try:
                from rosclaw.memory.interface import MemoryInterface
                self._memory = MemoryInterface(self.config.robot_id)
                self._modules.append(self._memory)
                print("[Runtime] Experience Grounding (Memory) initialized")
            except ImportError as e:
                print(f"[Runtime] Memory module not available: {e}")

        # Initialize Timeline Grounding (Practice)
        if self.config.enable_practice:
            try:
                from rosclaw.practice.recorder import PracticeRecorder
                self._practice = PracticeRecorder(
                    robot_id=self.config.robot_id,
                    joint_dof=self.config.joint_dof,
                )
                self._modules.append(self._practice)
                print("[Runtime] Timeline Grounding (Practice) initialized")
            except ImportError as e:
                print(f"[Runtime] Practice module not available: {e}")

        # Initialize Collaboration Grounding (Swarm)
        if self.config.enable_swarm:
            try:
                from rosclaw.swarm.manager import SwarmRuntimeManager
                self._swarm = SwarmRuntimeManager()
                self._modules.append(self._swarm)
                print("[Runtime] Collaboration Grounding (Swarm) initialized")
            except ImportError as e:
                print(f"[Runtime] Swarm module not available: {e}")

        # Initialize Skill Grounding (SkillManager)
        if self.config.enable_skill_manager:
            try:
                from rosclaw.skill_manager.registry import SkillRegistry
                from rosclaw.skill_manager.executor import SkillExecutor
                registry = SkillRegistry()
                self._skill_manager = SkillExecutor(self.event_bus, registry)
                self._modules.append(registry)
                self._modules.append(self._skill_manager)
                print("[Runtime] Skill Grounding (SkillManager) initialized")
            except ImportError as e:
                print(f"[Runtime] SkillManager module not available: {e}")

        # Initialize all module lifecycles
        for module in self._modules:
            if isinstance(module, LifecycleMixin):
                module.initialize()

        print("[Runtime] Initialization complete")

    def _do_start(self) -> None:
        """Start all modules."""
        print("[Runtime] Starting all modules...")
        for module in self._modules:
            if isinstance(module, LifecycleMixin) and module.is_ready:
                module.start()
        self.event_bus.publish(Event(
            topic="runtime.status",
            payload={"state": "running", "robot_id": self.config.robot_id},
            source="runtime",
            priority=EventPriority.HIGH,
        ))
        print("[Runtime] All modules started")

    def _do_stop(self) -> None:
        """Stop all modules gracefully."""
        print("[Runtime] Shutting down...")
        self.event_bus.publish(Event(
            topic="runtime.status",
            payload={"state": "shutting_down", "robot_id": self.config.robot_id},
            source="runtime",
            priority=EventPriority.CRITICAL,
        ))
        # Stop in reverse order
        for module in reversed(self._modules):
            if isinstance(module, LifecycleMixin):
                module.stop()
        print("[Runtime] Shutdown complete")

    def _setup_internal_subscriptions(self) -> None:
        """Set up internal EventBus subscriptions for runtime coordination."""
        self.event_bus.subscribe("safety.violation", self._on_safety_violation)
        self.event_bus.subscribe("agent.command", self._on_agent_command)
        self.event_bus.subscribe("robot.emergency_stop", self._on_emergency_stop)

    def _on_safety_violation(self, event: Event) -> None:
        """Handle safety violation events."""
        print(f"[Runtime] SAFETY VIOLATION: {event.payload}")
        self.event_bus.publish(Event(
            topic="robot.emergency_stop",
            payload={"reason": event.payload},
            source="runtime",
            priority=EventPriority.CRITICAL,
        ))

    def _on_agent_command(self, event: Event) -> None:
        """Handle agent commands - route to appropriate module."""
        command = event.payload.get("action", "")
        print(f"[Runtime] Agent command received: {command}")

    def _on_emergency_stop(self, event: Event) -> None:
        """Handle emergency stop - stop all drivers."""
        print("[Runtime] EMERGENCY STOP triggered")
        for driver in self._mcp_drivers.values():
            if hasattr(driver, "emergency_stop"):
                driver.emergency_stop()

    def register_driver(self, name: str, driver: Any) -> None:
        """Register an MCP driver with the runtime."""
        self._mcp_drivers[name] = driver
        print(f"[Runtime] Driver registered: {name}")

    def get_driver(self, name: str) -> Optional[Any]:
        """Get a registered driver by name."""
        return self._mcp_drivers.get(name)

    @property
    def firewall(self) -> Optional[Any]:
        return self._firewall

    @property
    def memory(self) -> Optional[Any]:
        return self._memory

    @property
    def practice(self) -> Optional[Any]:
        return self._practice

    @property
    def swarm(self) -> Optional[Any]:
        return self._swarm

    @property
    def skill_manager(self) -> Optional[Any]:
        return self._skill_manager

    @property
    def e_urdf(self) -> Optional[Any]:
        return self._e_urdf

    def get_status(self) -> dict:
        """Get comprehensive runtime status."""
        return {
            "robot_id": self.config.robot_id,
            "runtime_state": self.state.name,
            "event_bus": {
                "topics": self.event_bus.topics,
                "history_size": len(self.event_bus._event_history),
            },
            "modules": {
                "firewall": self._firewall is not None,
                "memory": self._memory is not None,
                "practice": self._practice is not None,
                "swarm": self._swarm is not None,
                "skill_manager": self._skill_manager is not None,
                "e_urdf": self._e_urdf is not None,
            },
            "drivers": list(self._mcp_drivers.keys()),
        }
