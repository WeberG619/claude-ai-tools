"""Reliable scroll helper using Windows Python + pyautogui
Usage: python scroll.py AMOUNT [--at X Y]
AMOUNT: positive = up, negative = down
"""
import sys
import pyautogui

pyautogui.FAILSAFE = False

def main():
    if len(sys.argv) < 2:
        print("Usage: python scroll.py AMOUNT [--at X Y]")
        print("  AMOUNT: positive = up, negative = down")
        sys.exit(1)

    amount = int(sys.argv[1])

    # Optional position
    x, y = None, None
    if "--at" in sys.argv:
        idx = sys.argv.index("--at")
        if idx + 2 < len(sys.argv):
            x = int(sys.argv[idx + 1])
            y = int(sys.argv[idx + 2])

    if x is not None and y is not None:
        pyautogui.scroll(amount, x=x, y=y)
        print(f"Scrolled {amount} at ({x}, {y})")
    else:
        pyautogui.scroll(amount)
        print(f"Scrolled {amount}")

if __name__ == "__main__":
    main()
