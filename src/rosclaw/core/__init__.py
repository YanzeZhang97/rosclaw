"""
ROSClaw Core - OS Kernel Layer

The core module provides the foundational runtime infrastructure:
- EventBus: Publish/subscribe message bus for all module communication
- Runtime: Central orchestrator managing all grounding engines
- Lifecycle: Module initialization, startup, and shutdown coordination
"""

from rosclaw.core.event_bus import EventBus, Event, EventPriority
from rosclaw.core.runtime import Runtime, RuntimeConfig
from rosclaw.core.lifecycle import LifecycleState, LifecycleMixin

__all__ = [
    "EventBus",
    "Event",
    "EventPriority",
    "Runtime",
    "RuntimeConfig",
    "LifecycleState",
    "LifecycleMixin",
]
