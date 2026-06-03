"""Shared helper to detect whether the ROS2 test environment is available."""

import os
import subprocess


def ros2_available() -> bool:
    """Return True if the ROS2 Python environment required by wrapper tests exists."""
    # Check for the dedicated ros2 venv
    ros2_python = "/tmp/ros2-venv/bin/python"
    if not os.path.exists(ros2_python):
        return False

    # Check that rclpy can be imported inside that interpreter
    try:
        result = subprocess.run(
            [ros2_python, "-c", "import rclpy; print('OK')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "OK" in result.stdout
    except Exception:
        return False
