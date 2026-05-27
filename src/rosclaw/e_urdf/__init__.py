"""
ROSClaw e-URDF - Physical DNA Parser

e-URDF (Embodied URDF) extends standard URDF with:
- Semantic annotations (grasp points, affordances)
- Physical properties (friction, mass distribution)
- Sensor configurations
- Control parameters

This is the Physical Grounding Engine - it gives LLMs
understanding of the robot's physical form.
"""

from rosclaw.e_urdf.parser import EURDFParser, RobotModel, JointSpec, LinkSpec

__all__ = ["EURDFParser", "RobotModel", "JointSpec", "LinkSpec"]
