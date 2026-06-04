"""rosclaw.darwin — Evaluation Pressure Module.

Darwin applies multi-seed benchmark stress to skills and detects
regressions before they reach real robots.
"""
from .plugin import DarwinPlugin
from .engine import DarwinEngine
from .events import DarwinBenchmarkCompletedEvent

__all__ = ["DarwinPlugin", "DarwinEngine", "DarwinBenchmarkCompletedEvent"]
