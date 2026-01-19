from __future__ import annotations

from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose

def main():
    with ReachyMini() as mini:
        print("Connected OK")

        # small, safe motion: look up slightly, then reset
        mini.goto_target(head=create_head_pose(z=8, degrees=True, mm=True), duration=1.0)
        mini.goto_target(head=create_head_pose(), duration=1.0)

        print("Motion OK")

if __name__ == "__main__":
    main()
