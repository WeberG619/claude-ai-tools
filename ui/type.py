"""Reliable typing helper using Windows Python + pyautogui
Usage: python type.py "text to type" [--enter] [--interval 0.05]
"""
import sys
import pyautogui

pyautogui.FAILSAFE = False

def main():
    if len(sys.argv) < 2:
        print('Usage: python type.py "text" [--enter] [--interval 0.05]')
        sys.exit(1)

    text = sys.argv[1]
    press_enter = "--enter" in sys.argv

    # Get typing interval if specified
    interval = 0.02  # default
    if "--interval" in sys.argv:
        idx = sys.argv.index("--interval")
        if idx + 1 < len(sys.argv):
            interval = float(sys.argv[idx + 1])

    pyautogui.write(text, interval=interval)

    if press_enter:
        pyautogui.press("enter")

    print(f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}")

if __name__ == "__main__":
    main()
