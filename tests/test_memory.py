"""Tests for Memory module."""

from rosclaw.memory.interface import MemoryInterface


def test_memory_store_and_query():
    mem = MemoryInterface("test_bot")
    mem.initialize()
    exp_id = mem.store_experience({"task_type": "pick", "data": "test"})
    assert exp_id.startswith("exp_")
    results = mem.query_experiences(task_type="pick")
    assert len(results) == 1
    assert results[0]["data"] == "test"
    mem.stop()


def test_memory_get_skill():
    mem = MemoryInterface("test_bot")
    mem.initialize()
    mem.store_experience({"skill_name": "grasp", "success": True})
    skill = mem.get_skill("grasp")
    assert skill is not None
    assert skill["skill_name"] == "grasp"
    mem.stop()


def test_memory_get_skill_missing():
    mem = MemoryInterface("test_bot")
    mem.initialize()
    assert mem.get_skill("nonexistent") is None
    mem.stop()
