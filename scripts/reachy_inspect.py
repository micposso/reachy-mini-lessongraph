"""Inspect ReachyMini SDK to discover available attributes and methods."""
from reachy_mini import ReachyMini

def inspect_object(obj, name="obj", depth=0, max_depth=2):
    """Recursively inspect an object's attributes."""
    indent = "  " * depth

    # Get all public attributes
    attrs = [a for a in dir(obj) if not a.startswith("_")]

    print(f"{indent}{name}: {type(obj).__name__}")

    if depth >= max_depth:
        print(f"{indent}  (max depth reached)")
        return

    for attr in attrs:
        try:
            val = getattr(obj, attr)
            if callable(val):
                print(f"{indent}  .{attr}() - method")
            elif hasattr(val, "__dict__") and not isinstance(val, (str, int, float, bool, list, dict, tuple)):
                # It's a sub-object, inspect it
                print(f"{indent}  .{attr}:")
                inspect_object(val, attr, depth + 1, max_depth)
            else:
                print(f"{indent}  .{attr} = {repr(val)[:60]}")
        except Exception as e:
            print(f"{indent}  .{attr} - error: {e}")

def main():
    print("Connecting to ReachyMini...")
    with ReachyMini() as mini:
        print("\n=== ReachyMini SDK Inspection ===\n")
        inspect_object(mini, "mini", max_depth=2)

        # Also print the raw dir() output
        print("\n=== All attributes (dir) ===")
        attrs = [a for a in dir(mini) if not a.startswith("_")]
        print(attrs)

if __name__ == "__main__":
    main()
