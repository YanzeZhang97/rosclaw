"""Skill Registry - Skill registration and discovery."""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from rosclaw.core.lifecycle import LifecycleMixin


@dataclass
class SkillEntry:
    """Represents a registered skill."""
    name: str
    description: str
    skill_type: str  # "programmed", "learned", "hybrid"
    parameters: dict[str, Any] = field(default_factory=dict)
    preconditions: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    execution_count: int = 0
    success_rate: float = 0.0
    handler: Optional[Callable] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "success_criteria": self.success_criteria,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "execution_count": self.execution_count,
            "success_rate": self.success_rate,
            "metadata": self.metadata,
        }


class SkillRegistry(LifecycleMixin):
    """
    Central registry for all robot skills.

    Skills can be:
    - Programmed: Hand-written control logic
    - Learned: Generated from demonstrations via AI
    - Hybrid: Programmed skeleton with learned parameters
    """

    def __init__(self):
        super().__init__()
        self._skills: dict[str, SkillEntry] = {}

    def _do_initialize(self) -> None:
        print("[SkillRegistry] Initialized")

    def register(self, entry: SkillEntry) -> None:
        """Register a skill."""
        if entry.name in self._skills:
            print(f"[SkillRegistry] Overwriting skill: {entry.name}")
        self._skills[entry.name] = entry
        print(f"[SkillRegistry] Registered skill: {entry.name} ({entry.skill_type})")

    def unregister(self, name: str) -> bool:
        """Remove a skill from registry."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> Optional[SkillEntry]:
        """Retrieve a skill by name."""
        return self._skills.get(name)

    def list_skills(self, skill_type: Optional[str] = None) -> list[str]:
        """List all registered skill names."""
        if skill_type:
            return [s.name for s in self._skills.values() if s.skill_type == skill_type]
        return list(self._skills.keys())

    def find_by_precondition(self, precondition: str) -> list[SkillEntry]:
        """Find skills matching a precondition."""
        return [s for s in self._skills.values() if precondition in s.preconditions]

    def update_stats(self, name: str, success: bool) -> None:
        """Update execution statistics for a skill."""
        skill = self._skills.get(name)
        if skill is None:
            return
        skill.execution_count += 1
        if success:
            skill.success_rate = (
                (skill.success_rate * (skill.execution_count - 1) + 1.0)
                / skill.execution_count
            )
        else:
            skill.success_rate = (
                skill.success_rate * (skill.execution_count - 1)
            ) / skill.execution_count
        skill.updated_at = time.time()

    @property
    def count(self) -> int:
        return len(self._skills)
