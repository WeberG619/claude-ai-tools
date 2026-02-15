"""Reliable click helper using Windows Python + pyautogui
Usage: python click.py X Y [--double] [--right]
"""
import sys
import pyautogui

pyautogui.FAILSAFE = False  # Don't fail if mouse goes to corner

def main():
    if len(sys.argv) < 3:
        print("Usage: python click.py X Y [--double] [--right]")
        sys.exit(1)

    x = int(sys.argv[1])
    y = int(sys.argv[2])
    double = "--double" in sys.argv
    right = "--right" in sys.argv

    button = "right" if right else "left"
    clicks = 2 if double else 1

    pyautogui.click(x, y, clicks=clicks, button=button)
    print(f"Clicked at ({x}, {y}) button={button} clicks={clicks}")

if __name__ == "__main__":
    main()
