"""Quick test to verify the ReachyMiniRobot works correctly."""
import os

# Ensure we're using the reachy backend
os.environ.setdefault("ROBOT_BACKEND", "reachy")

from reachy_teacher.io.robot_factory import get_robot


def main():
    print(f"ROBOT_BACKEND = {os.getenv('ROBOT_BACKEND')}")

    robot = get_robot()
    print(f"Robot type: {type(robot).__name__}")

    try:
        print("\n[1] Opening robot connection...")
        if hasattr(robot, "open"):
            robot.open()
            print("  Robot opened successfully")

        print("\n[2] Testing emotion (happy)...")
        robot.set_emotion("happy")
        print("  Emotion set")

        print("\n[3] Testing motion (nod)...")
        robot.do_motion("nod")
        print("  Motion done")

        print("\n[4] Testing TTS...")
        robot.say("Hello! I am Reachy Mini. The robot connection is working.")
        print("  TTS done")

        print("\n[5] Testing ask and listen...")
        response = robot.ask_and_listen_text("Can you hear me? Please say yes.", record_seconds=4.0)
        print(f"  You said: '{response}'")

        print("\n[6] Confirming response...")
        if response:
            robot.say(f"Great! I heard you say: {response}")
        else:
            robot.say("I didn't hear anything clearly.")

        print("\nAll tests passed!")

    finally:
        print("\n[7] Closing robot...")
        if hasattr(robot, "close"):
            robot.close()
        print("  Robot closed")


if __name__ == "__main__":
    main()
