from reachy_mini import ReachyMini

def main():
    mini = ReachyMini(localhost_only=False, spawn_daemon=False, timeout=10.0)
    print("Connected OK:", mini)

if __name__ == "__main__":
    main()
