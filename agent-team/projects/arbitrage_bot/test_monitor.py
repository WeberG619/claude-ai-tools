"""
Test file to demonstrate live monitor auto-switching.
Written at: {timestamp}

This file should trigger the monitor to:
1. Switch from photo_intelligence to arbitrage_bot
2. Show this file's content
3. Display the green "writing" indicator
"""

import time

def main():
    """This function was created to test the live code view."""
    print("Live monitor test successful!")
    print(f"File written at: {time.strftime('%H:%M:%S')}")

    # The monitor should have auto-switched to show this file
    return True

if __name__ == "__main__":
    main()
