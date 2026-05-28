"""rosclaw_how.recovery — Recovery strategy execution helpers.

Provides utility functions for formatting recovery suggestions into
EventBus payloads and for applying common recovery transformations
(e.g., reduce velocity, replan, increase timeout).

This module is stateless; it does not interact with SeekDB.
"""
from __future__ import annotations

from typing import Any, Optional


class RecoveryFormatter:
    """Format recovery suggestions into EventBus-compatible payloads."""

    @staticmethod
    def to_event_payload(
        rule: dict[str, Any],
        *,
        request_id: str = "",
        source: str = "heuristic_engine",
    ) -> dict[str, Any]:
        """Convert a rule dict into an EventBus payload."""
        return {
            "request_id": request_id,
            "rule_id": rule.get("rule_id", ""),
            "condition": rule.get("condition", ""),
            "suggestion": rule.get("action", ""),
            "priority": rule.get("priority", 0),
            "source": rule.get("source", source),
            "success_count": rule.get("success_count", 0),
            "failure_count": rule.get("failure_count", 0),
        }

    @staticmethod
    def apply_trajectory_adjustment(
        trajectory: list[list[float]],
        suggestion: str,
    ) -> list[list[float]]:
        """Best-effort trajectory adjustment based on suggestion text.

        This is a naive implementation for v1.0. v1.1 should use
        the full rosclaw-how service with vector search and diff snippets.
        """
        suggestion_lower = suggestion.lower()

        # Reduce velocity / joint limits
        if "reduce" in suggestion_lower and ("velocity" in suggestion_lower or "kp" in suggestion_lower):
            factor = 0.5 if "50" in suggestion_lower else 0.7
            return [[v * factor for v in wp] for wp in trajectory]

        # Increase grip force (add small offset to last DOF if gripper)
        if "grip" in suggestion_lower and "force" in suggestion_lower:
            offset = 0.2 if "20" in suggestion_lower else 0.1
            return [
                wp[:-1] + [wp[-1] + offset] if wp else wp
                for wp in trajectory
            ]

        # Default: no transformation
        return list(trajectory)


def format_recovery_suggestion(
    recovery: Optional[dict[str, Any]],
    *,
    request_id: str = "",
) -> str:
    """Human-readable recovery suggestion string."""
    if not recovery:
        return "No heuristic recovery available."
    action = recovery.get("action", "")
    source = recovery.get("source", "heuristic")
    return f"[{source}] {action}"
