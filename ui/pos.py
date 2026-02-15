"""Get current mouse position and screen info
Usage: python pos.py [--watch]
"""
import sys
import pyautogui
import time

def main():
    if "--watch" in sys.argv:
        print("Watching mouse position (Ctrl+C to stop)...")
        try:
            while True:
                x, y = pyautogui.position()
                print(f"\rPosition: ({x}, {y})    ", end="", flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        x, y = pyautogui.position()
        screen_w, screen_h = pyautogui.size()
        print(f"Mouse position: ({x}, {y})")
        print(f"Screen size: {screen_w} x {screen_h}")

if __name__ == "__main__":
    main()
