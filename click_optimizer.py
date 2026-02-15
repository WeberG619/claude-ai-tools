#!/usr/bin/env python3
"""
Click Optimizer - Fixes click accuracy and speed issues
Weber Gouin - BIM Ops Studio
February 2026
"""

import time
import json
import subprocess
from pathlib import Path
import pyautogui
import win32gui
import win32api
import win32con
from typing import Tuple, Optional

# Disable pyautogui failsafe for production use
pyautogui.FAILSAFE = False
# Speed up mouse movement
pyautogui.PAUSE = 0.01  # Reduced from default 0.1
pyautogui.MINIMUM_DURATION = 0  # Instant movements
pyautogui.MINIMUM_SLEEP = 0.001  # Faster sleep

class ClickOptimizer:
    """Optimized clicking with monitor awareness and retry logic"""

    def __init__(self):
        # Monitor configuration
        self.monitors = {
            'left': {'x': -5120, 'y': 0, 'width': 2560, 'height': 1440},
            'center': {'x': -2560, 'y': 0, 'width': 2560, 'height': 1440},
            'right': {'x': 0, 'y': 0, 'width': 2560, 'height': 1440}
        }

        # Click optimization settings
        self.click_delay = 0.05  # 50ms between actions
        self.max_retries = 3
        self.verify_window = True

    def get_window_rect(self, title_contains: str) -> Optional[Tuple[int, int, int, int]]:
        """Get window rectangle by partial title match"""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if title_contains.lower() in window_text.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append((hwnd, rect))
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            hwnd, rect = windows[0]
            return rect
        return None

    def bring_window_to_front(self, title_contains: str) -> bool:
        """Bring window to foreground"""
        def callback(hwnd, result):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if title_contains.lower() in window_text.lower():
                    result.append(hwnd)
            return True

        result = []
        win32gui.EnumWindows(callback, result)

        if result:
            hwnd = result[0]
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # Bring to front
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)  # Brief wait for window activation
            return True
        return False

    def fast_click(self, x: int, y: int, button='left', clicks=1, verify_position=True):
        """Optimized clicking with verification"""
        # Move mouse quickly
        win32api.SetCursorPos((x, y))

        # Verify position if needed
        if verify_position:
            actual_x, actual_y = win32api.GetCursorPos()
            if abs(actual_x - x) > 5 or abs(actual_y - y) > 5:
                # Retry positioning
                win32api.SetCursorPos((x, y))
                time.sleep(0.01)

        # Perform click(s)
        for _ in range(clicks):
            if button == 'left':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            elif button == 'right':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)

            if clicks > 1:
                time.sleep(0.05)  # Brief delay between multiple clicks

    def smart_click(self, x: int, y: int, window_title: str = None, **kwargs):
        """Smart click with window focus and retry logic"""
        # Focus window if specified
        if window_title:
            if not self.bring_window_to_front(window_title):
                print(f"Warning: Could not find window containing '{window_title}'")

        # Try clicking with retries
        for attempt in range(self.max_retries):
            try:
                self.fast_click(x, y, **kwargs)
                return True
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"Click attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    print(f"Click failed after {self.max_retries} attempts: {e}")
                    return False

        return True

    def get_monitor_for_coords(self, x: int, y: int) -> str:
        """Determine which monitor contains the coordinates"""
        for name, bounds in self.monitors.items():
            if (bounds['x'] <= x < bounds['x'] + bounds['width'] and
                bounds['y'] <= y < bounds['y'] + bounds['height']):
                return name
        return 'unknown'

    def optimize_browser_clicks(self):
        """Optimize browser automation settings"""
        settings = {
            'click_delay': 50,  # ms
            'scroll_delay': 100,  # ms
            'type_delay': 10,  # ms per character
            'wait_for_element': 500,  # ms max wait
            'use_hardware_acceleration': True,
            'prefer_native_events': True,
            'double_click_speed': 200  # ms
        }

        # Save optimized settings
        settings_path = Path('/mnt/d/_CLAUDE-TOOLS/browser_settings.json')
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)

        print(f"Browser automation settings optimized and saved to {settings_path}")
        return settings

    def test_click_speed(self):
        """Test click speed and accuracy"""
        print("Testing click performance...")

        # Test rapid clicks
        start = time.time()
        test_coords = [(100, 100), (200, 200), (300, 300), (400, 400), (500, 500)]

        for x, y in test_coords:
            self.fast_click(x, y, verify_position=False)

        elapsed = time.time() - start
        avg_time = elapsed / len(test_coords) * 1000  # Convert to ms

        print(f"Average click time: {avg_time:.1f}ms")
        print(f"Total time for {len(test_coords)} clicks: {elapsed:.3f}s")

        if avg_time > 100:
            print("⚠️ Click speed is slower than optimal. Adjusting settings...")
            pyautogui.PAUSE = 0.001
            pyautogui.MINIMUM_DURATION = 0
        else:
            print("✓ Click speed is optimal")

        return avg_time

def main():
    """Initialize and test click optimizer"""
    print("Click Optimizer v1.0 - BIM Ops Studio")
    print("=" * 50)

    optimizer = ClickOptimizer()

    # Run optimizations
    print("\n1. Optimizing browser automation...")
    optimizer.optimize_browser_clicks()

    print("\n2. Testing click performance...")
    avg_time = optimizer.test_click_speed()

    print("\n3. System recommendations:")
    if avg_time < 50:
        print("✓ System is performing optimally")
    else:
        print("Recommendations to improve performance:")
        print("- Close unnecessary applications")
        print("- Disable Windows animations")
        print("- Check for GPU driver updates")
        print("- Consider increasing process priority")

    print("\nOptimization complete!")
    print("\nUsage example:")
    print("  from click_optimizer import ClickOptimizer")
    print("  opt = ClickOptimizer()")
    print("  opt.smart_click(x=500, y=300, window_title='Chrome')")

if __name__ == '__main__':
    main()