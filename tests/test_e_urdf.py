"""Tests for e-URDF module."""

import pytest

from rosclaw.e_urdf.parser import EURDFParser, RobotModel, JointSpec, LinkSpec


def test_robot_model_creation():
    model = RobotModel(name="test_arm")
    assert model.name == "test_arm"
    assert len(model.joints) == 0


def test_joint_spec():
    joint = JointSpec(name="j1", joint_type="revolute", parent="base", child="link1", limits={"lower": -3.14, "upper": 3.14})
    assert joint.joint_type == "revolute"
    assert joint.limits["lower"] == -3.14
    assert joint.limits["upper"] == 3.14


def test_link_spec():
    link = LinkSpec(name="base", mass=1.0)
    assert link.mass == 1.0


def test_eurdf_parser_mock():
    with pytest.raises(FileNotFoundError):
        EURDFParser("/nonexistent.urdf")


def test_to_llm_context():
    model = RobotModel(name="test_bot")
    model.joints["j1"] = JointSpec(name="j1", joint_type="revolute", parent="base", child="l1", limits={"lower": -1.0, "upper": 1.0})
    model.links["l1"] = LinkSpec(name="l1", mass=0.5)
    ctx = model.to_llm_context()
    assert "test_bot" in ctx
    assert "Degrees of Freedom: 1" in ctx
