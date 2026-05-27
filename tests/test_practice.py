"""Tests for Practice module."""

from rosclaw.practice.recorder import PracticeRecorder
from rosclaw.data.flywheel import EventType


def test_practice_lifecycle():
    rec = PracticeRecorder("test_bot", joint_dof=6)
    rec.initialize()
    assert rec.is_ready
    rec.start_recording()
    assert rec.is_recording is True
    rec.stop_recording()
    assert rec.is_recording is False
    rec.stop()


def test_practice_mark_event():
    rec = PracticeRecorder("test_bot", joint_dof=6)
    rec.initialize()
    rec.start_recording()
    event_id = rec.mark_event(EventType.SUCCESS, {"task": "test"})
    assert event_id != ""
    rec.stop()
