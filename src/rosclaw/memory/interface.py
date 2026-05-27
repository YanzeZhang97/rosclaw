"""
Memory Interface - Experience Grounding

Provides access to the SeekDB shared knowledge plane.
This is a placeholder interface that will be integrated with
the actual rosclaw-memory implementation.
"""

from typing import Any, Optional

from rosclaw.core.lifecycle import LifecycleMixin


class MemoryInterface(LifecycleMixin):
    """
    Interface to robot memory / experience storage.

    Stores and retrieves:
    - Task execution history
    - Successful skill demonstrations
    - World state observations
    - Failure modes and recovery strategies
    """

    def __init__(self, robot_id: str):
        super().__init__()
        self.robot_id = robot_id
        self._experiences: list[dict] = []

    def _do_initialize(self) -> None:
        """Initialize memory connection."""
        print(f"[Memory] Initializing memory interface for {self.robot_id}")

    def store_experience(self, experience: dict) -> str:
        """Store a new experience."""
        exp_id = f"exp_{len(self._experiences)}"
        experience["id"] = exp_id
        experience["robot_id"] = self.robot_id
        self._experiences.append(experience)
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
