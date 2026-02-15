"""Move mouse helper using Windows Python + pyautogui
Usage: python move.py X Y [--duration 0.25]
"""
import sys
import pyautogui

pyautogui.FAILSAFE = False

def main():
    if len(sys.argv) < 3:
        print("Usage: python move.py X Y [--duration 0.25]")
        sys.exit(1)

    x = int(sys.argv[1])
    y = int(sys.argv[2])

    duration = 0.1  # default
    if "--duration" in sys.argv:
        idx = sys.argv.index("--duration")
        if idx + 1 < len(sys.argv):
            duration = float(sys.argv[idx + 1])

    pyautogui.moveTo(x, y, duration=duration)
    print(f"Moved to ({x}, {y})")

if __name__ == "__main__":
    main()
