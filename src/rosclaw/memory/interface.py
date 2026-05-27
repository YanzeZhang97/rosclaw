"""Memory Interface - Experience Grounding

Provides access to the SeekDB shared knowledge plane.
All communication goes through EventBus — no direct module calls.
"""

from typing import Any, Optional

from rosclaw.core.event_bus import EventBus, Event, EventPriority
from rosclaw.core.lifecycle import LifecycleMixin


class MemoryInterface(LifecycleMixin):
    """
    Interface to robot memory / experience storage.

    Stores and retrieves experiences via EventBus:
    - Subscribes to praxis.completed / praxis.failed for auto-storage
    - Publishes memory.query results for async consumption
    """

    def __init__(self, robot_id: str, event_bus: Optional[EventBus] = None):
        super().__init__()
        self.robot_id = robot_id
        self.event_bus = event_bus
        self._experiences: list[dict] = []

    def _do_initialize(self) -> None:
        print(f"[Memory] Initializing memory interface for {self.robot_id}")
        if self.event_bus is not None:
            self.event_bus.subscribe("praxis.completed", self._on_praxis_completed)
            self.event_bus.subscribe("praxis.failed", self._on_praxis_failed)
            self.event_bus.subscribe("memory.query", self._on_memory_query)

    def _do_stop(self) -> None:
        if self.event_bus is not None:
            self.event_bus.unsubscribe("praxis.completed", self._on_praxis_completed)
            self.event_bus.unsubscribe("praxis.failed", self._on_praxis_failed)
            self.event_bus.unsubscribe("memory.query", self._on_memory_query)

    def _on_praxis_completed(self, event: Event) -> None:
        """Auto-store successful praxis events."""
        self.store_experience({
            "task_type": "praxis",
            "event": event.payload,
            "robot_id": self.robot_id,
        })

    def _on_praxis_failed(self, event: Event) -> None:
        """Auto-store failed praxis events."""
        self.store_experience({
            "task_type": "praxis_failure",
            "event": event.payload,
            "robot_id": self.robot_id,
        })

    def _on_memory_query(self, event: Event) -> None:
        """Handle async memory queries via EventBus."""
        payload = event.payload if isinstance(event.payload, dict) else {}
        task_type = payload.get("task_type")
        limit = payload.get("limit", 10)
        results = self.query_experiences(task_type=task_type, limit=limit)
        if self.event_bus is not None:
            self.event_bus.publish(Event(
                topic="memory.query_result",
                payload={"query": payload, "results": results},
                source="memory",
                priority=EventPriority.NORMAL,
            ))

    def store_experience(self, experience: dict) -> str:
        """Store a new experience."""
        exp_id = f"exp_{len(self._experiences)}"
        experience["id"] = exp_id
        experience["robot_id"] = self.robot_id
        self._experiences.append(experience)
        # Publish storage event for other modules
        if self.event_bus is not None:
            self.event_bus.publish(Event(
                topic="memory.stored",
                payload={"exp_id": exp_id, "experience": experience},
                source="memory",
                priority=EventPriority.LOW,
            ))
        return exp_id

    def query_experiences(self, task_type: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Query stored experiences."""
        results = self._experiences
        if task_type:
            results = [e for e in results if e.get("task_type") == task_type]
        return results[-limit:]

    def get_skill(self, skill_name: str) -> Optional[dict]:
        """Retrieve a learned skill by name."""
        for exp in reversed(self._experiences):
            if exp.get("skill_name") == skill_name:
                return exp
        return None
