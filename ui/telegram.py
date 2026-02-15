"""Telegram automation using Windows UI Automation
Usage:
  python telegram.py send "message text"
  python telegram.py focus
  python telegram.py info
"""
import sys
from pywinauto import Application, Desktop

def find_telegram():
    """Find Telegram window"""
    desktop = Desktop(backend="uia")
    windows = desktop.windows(title_re=".*Telegram.*|.*BotFather.*")
    if windows:
        return windows[0]
    return None

def send_message(text):
    """Send a message in the currently open Telegram chat"""
    try:
        # Connect to Telegram
        app = Application(backend="uia").connect(title_re=".*Telegram.*|.*BotFather.*")
        win = app.top_window()
        win.set_focus()

        # Find the message input (usually an Edit control)
        # Try different methods to find the input
        try:
            # Method 1: Find by control type
            edit = win.child_window(control_type="Edit", found_index=0)
            edit.set_focus()
            edit.type_keys(text, with_spaces=True)
            edit.type_keys("{ENTER}")
            print(f"Sent: {text}")
            return True
        except Exception as e1:
            print(f"Method 1 failed: {e1}")

            # Method 2: Just type if window is focused
            import pyautogui
            pyautogui.write(text, interval=0.02)
            pyautogui.press("enter")
            print(f"Sent via pyautogui: {text}")
            return True

    except Exception as e:
        print(f"Error: {e}")
        return False

def focus_telegram():
    """Bring Telegram to foreground"""
    try:
        app = Application(backend="uia").connect(title_re=".*Telegram.*|.*BotFather.*")
        win = app.top_window()
        win.set_focus()
        print(f"Focused: {win.window_text()}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def show_info():
    """Show info about Telegram window"""
    try:
        app = Application(backend="uia").connect(title_re=".*Telegram.*|.*BotFather.*")
        win = app.top_window()
        print(f"Window: {win.window_text()}")
        print(f"Rectangle: {win.rectangle()}")
        print("\nChild elements:")
        win.print_control_identifiers(depth=2)
    except Exception as e:
        print(f"Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python telegram.py [send|focus|info] [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "send" and len(sys.argv) >= 3:
        text = " ".join(sys.argv[2:])
        send_message(text)
    elif cmd == "focus":
        focus_telegram()
    elif cmd == "info":
        show_info()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
