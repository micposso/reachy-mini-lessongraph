from reachy_teacher.io.robot_reachy_media import ReachyMiniRobot

def main():
    robot = ReachyMiniRobot().open()
    try:
        robot.say("Adapter smoke test. Say hello Reachy.")
        text = robot.ask_and_listen_text("Say: hello Reachy.", record_seconds=4.0)
        robot.say(f"I heard: {text if text else 'nothing clear'}")
    finally:
        robot.close()

if __name__ == "__main__":
    main()
