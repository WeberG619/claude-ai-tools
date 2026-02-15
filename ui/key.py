"""Key press helper using Windows Python + pyautogui
Usage: python key.py KEY [KEY2 KEY3...]
       python key.py --hotkey ctrl c
Examples:
  python key.py enter
  python key.py tab tab enter
  python key.py --hotkey ctrl shift s
"""
import sys
import pyautogui

pyautogui.FAILSAFE = False

def main():
    if len(sys.argv) < 2:
        print("Usage: python key.py KEY [KEY2...]")
        print("       python key.py --hotkey ctrl c")
        sys.exit(1)

    if sys.argv[1] == "--hotkey":
        # Hotkey mode: press all keys together
        keys = sys.argv[2:]
        pyautogui.hotkey(*keys)
        print(f"Hotkey: {'+'.join(keys)}")
    else:
        # Sequential key presses
        for key in sys.argv[1:]:
            pyautogui.press(key)
        print(f"Pressed: {' '.join(sys.argv[1:])}")

if __name__ == "__main__":
    main()
