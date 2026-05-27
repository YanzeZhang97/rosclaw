"""Tests for Swarm module."""

from rosclaw.swarm.manager import SwarmRuntimeManager


def test_swarm_register_agent():
    swarm = SwarmRuntimeManager()
    swarm.initialize()
    swarm.register_agent("bot_1", ["pick", "place"])
    assert swarm.agent_count == 1
    status = swarm.get_agent_status("bot_1")
    assert status["status"] == "idle"
    swarm.stop()


def test_swarm_allocate_task():
    swarm = SwarmRuntimeManager()
    swarm.initialize()
    swarm.register_agent("bot_1", ["pick"])
    agent = swarm.allocate_task({"required_capabilities": ["pick"], "id": "task_1"})
    assert agent == "bot_1"
    swarm.stop()


def test_swarm_allocate_no_match():
    swarm = SwarmRuntimeManager()
    swarm.initialize()
    swarm.register_agent("bot_1", ["pick"])
    agent = swarm.allocate_task({"required_capabilities": ["place"]})
    assert agent is None
    swarm.stop()
