import os
from .robot_mock import RobotMock
from .robot_reachy_media import ReachyMiniRobot

def get_robot():
    backend = os.getenv("ROBOT_BACKEND", "mock").strip().lower()
    if backend == "reachy":
        return ReachyMiniRobot()
    return RobotMock()
