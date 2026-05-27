"""
Practice Recorder - Timeline Grounding

Records robot execution traces using the DataFlywheel.
Provides black-box recording for later analysis, replay, and learning.
"""

from pathlib import Path
from typing import Any, Optional

from rosclaw.core.lifecycle import LifecycleMixin
from rosclaw.data.flywheel import DataFlywheel, EventType


class PracticeRecorder(LifecycleMixin):
    """
    Records robot practice sessions and execution traces.

    Uses the DataFlywheel for high-frequency capture
    and event-triggered persistence.
    """

    def __init__(self, robot_id: str, joint_dof: int = 6):
        super().__init__()
        self.robot_id = robot_id
        self.joint_dof = joint_dof
        self._flywheel: Optional[DataFlywheel] = None
        self._recording = False

    def _do_initialize(self) -> None:
        """Initialize the practice recorder."""
        self._flywheel = DataFlywheel(
            robot_id=self.robot_id,
            joint_dof=self.joint_dof,
        )
        print(f"[Practice] Recorder initialized for {self.robot_id}")

    def start_recording(self) -> None:
        """Start a recording session."""
        self._recording = True
        print("[Practice] Recording started")

    def stop_recording(self) -> None:
        """Stop recording."""
        self._recording = False
        print("[Practice] Recording stopped")

    def log_state(self, joint_positions: list[float], timestamp: float) -> None:
        """Log a robot state sample."""
        if not self._recording or self._flywheel is None:
            return
        from rosclaw.data.flywheel import RobotState as FlywheelRobotState
        import numpy as np
        state = FlywheelRobotState(
            timestamp=timestamp,
            joint_positions=np.array(joint_positions),
            joint_velocities=np.zeros(self.joint_dof),
            joint_torques=np.zeros(self.joint_dof),
        )
        self._flywheel.on_control_cycle(state)

    def mark_event(self, event_type: EventType, metadata: Optional[dict] = None) -> str:
        """Mark an event in the recording."""
        if self._flywheel is None:
            return ""
        return self._flywheel.trigger_event(event_type, metadata)

    def export_session(self, output_path: Path) -> Path:
        """Export recorded session to LeRobot format."""
        if self._flywheel is None:
            raise RuntimeError("Flywheel not initialized")
        return self._flywheel.export_to_lerobot(output_path)

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
