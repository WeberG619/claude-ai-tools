"""
Human Behavior Simulation
Makes browser automation look natural and human-like
"""

import random
import time
import math
from typing import Tuple

from selenium.webdriver.common.action_chains import ActionChains


class HumanBehavior:
    """
    Simulates human-like behavior for browser automation.

    Features:
    - Random delays between actions
    - Natural mouse movements (not straight lines)
    - Typing with variable speed
    - Random micro-pauses
    """

    def __init__(self):
        # Typing speed (characters per second, varies per "user")
        self.base_typing_speed = random.uniform(5, 12)  # chars/sec
        # Mouse movement smoothness
        self.mouse_steps = random.randint(15, 25)

    def random_delay(self, min_sec: float = 0.1, max_sec: float = 0.5):
        """Add a random delay to simulate human reaction time"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def typing_delay(self) -> float:
        """Get delay between keystrokes (varies naturally)"""
        # Base delay from typing speed
        base_delay = 1.0 / self.base_typing_speed

        # Add natural variation (+/- 50%)
        variation = random.uniform(0.5, 1.5)

        # Occasionally add longer pauses (thinking/correcting)
        if random.random() < 0.05:  # 5% chance
            variation *= random.uniform(2, 5)

        return base_delay * variation

    def human_type(self, element, text: str):
        """
        Type text with human-like timing.

        Includes:
        - Variable delay between characters
        - Occasional pauses (like thinking)
        - Different speeds for different character types
        """
        for i, char in enumerate(text):
            # Type the character
            element.send_keys(char)

            # Get base delay
            delay = self.typing_delay()

            # Adjust for character type
            if char in ' \n\t':
                # Slightly longer pause after spaces/newlines
                delay *= random.uniform(1.2, 1.8)
            elif char in '.,!?':
                # Pause after punctuation
                delay *= random.uniform(1.5, 2.5)
            elif char.isupper() and i > 0 and not text[i-1].isupper():
                # Slight delay for shift key
                delay *= random.uniform(1.1, 1.3)

            time.sleep(delay)

    def bezier_curve(self, start: Tuple[int, int], end: Tuple[int, int],
                    num_points: int = 20) -> list:
        """
        Generate points along a bezier curve for smooth mouse movement.
        Creates natural, curved paths instead of straight lines.
        """
        # Add control points for curve
        ctrl1 = (
            start[0] + random.randint(-50, 50) + (end[0] - start[0]) * 0.3,
            start[1] + random.randint(-50, 50) + (end[1] - start[1]) * 0.3
        )
        ctrl2 = (
            start[0] + random.randint(-50, 50) + (end[0] - start[0]) * 0.7,
            start[1] + random.randint(-50, 50) + (end[1] - start[1]) * 0.7
        )

        points = []
        for i in range(num_points + 1):
            t = i / num_points

            # Cubic bezier formula
            x = (1-t)**3 * start[0] + \
                3 * (1-t)**2 * t * ctrl1[0] + \
                3 * (1-t) * t**2 * ctrl2[0] + \
                t**3 * end[0]

            y = (1-t)**3 * start[1] + \
                3 * (1-t)**2 * t * ctrl1[1] + \
                3 * (1-t) * t**2 * ctrl2[1] + \
                t**3 * end[1]

            # Add tiny random jitter (hand tremor simulation)
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)

            points.append((int(x), int(y)))

        return points

    def human_move_to_element(self, driver, element):
        """
        Move mouse to element with human-like curved movement.

        Args:
            driver: Selenium WebDriver instance
            element: Target element to move to
        """
        try:
            # Get element location
            location = element.location
            size = element.size

            # Target somewhere within the element (not always center)
            target_x = location['x'] + random.uniform(0.2, 0.8) * size['width']
            target_y = location['y'] + random.uniform(0.2, 0.8) * size['height']

            # Get current mouse position (approximate from last known)
            # Note: Selenium doesn't expose current mouse position, so we estimate
            viewport_width = driver.execute_script("return window.innerWidth")
            viewport_height = driver.execute_script("return window.innerHeight")

            # Random starting point (simulate unknown cursor position)
            start_x = random.randint(0, viewport_width)
            start_y = random.randint(0, viewport_height)

            # Generate curved path
            path = self.bezier_curve(
                (start_x, start_y),
                (int(target_x), int(target_y)),
                self.mouse_steps
            )

            # Move along the path
            actions = ActionChains(driver)
            for point in path:
                actions.move_by_offset(
                    point[0] - (path[0][0] if path.index(point) == 0 else path[path.index(point)-1][0]),
                    point[1] - (path[0][1] if path.index(point) == 0 else path[path.index(point)-1][1])
                )

                # Small delay between movements
                if random.random() < 0.3:  # 30% chance of micro-pause
                    time.sleep(random.uniform(0.001, 0.01))

            # Move to element (final adjustment)
            actions.move_to_element(element)
            actions.perform()

        except Exception:
            # Fallback to simple move
            actions = ActionChains(driver)
            actions.move_to_element(element)
            actions.perform()

    def scroll_human_like(self, driver, pixels: int, direction: str = "down"):
        """
        Scroll with human-like behavior (not instant jumps).

        Args:
            driver: Selenium WebDriver instance
            pixels: Total pixels to scroll
            direction: 'up' or 'down'
        """
        scrolled = 0
        while scrolled < pixels:
            # Random chunk size (humans scroll in uneven amounts)
            chunk = random.randint(50, 150)
            if scrolled + chunk > pixels:
                chunk = pixels - scrolled

            if direction == "down":
                driver.execute_script(f"window.scrollBy(0, {chunk});")
            else:
                driver.execute_script(f"window.scrollBy(0, -{chunk});")

            scrolled += chunk

            # Random delay between scroll chunks
            time.sleep(random.uniform(0.05, 0.2))

            # Occasional longer pause (reading content)
            if random.random() < 0.1:  # 10% chance
                time.sleep(random.uniform(0.5, 1.5))

    def random_mouse_wiggle(self, driver):
        """
        Perform small random mouse movements.
        Humans don't hold the mouse perfectly still.
        """
        actions = ActionChains(driver)
        for _ in range(random.randint(2, 5)):
            actions.move_by_offset(
                random.randint(-10, 10),
                random.randint(-10, 10)
            )
            time.sleep(random.uniform(0.1, 0.3))
        actions.perform()

    def simulate_reading_time(self, text_length: int):
        """
        Add delay based on content length (simulating reading).

        Average reading speed: ~250 words/minute
        Average word length: ~5 characters
        """
        words = text_length / 5
        reading_time = words / 250 * 60  # Convert to seconds

        # Add variation (some people read faster/slower)
        reading_time *= random.uniform(0.7, 1.3)

        # Cap at reasonable maximum
        reading_time = min(reading_time, 10)

        time.sleep(reading_time)


if __name__ == "__main__":
    # Test human behavior
    human = HumanBehavior()

    print("Testing random delays...")
    for i in range(5):
        human.random_delay(0.1, 0.5)
        print(f"  Delay {i+1} completed")

    print("\nTesting typing delays...")
    for i in range(10):
        delay = human.typing_delay()
        print(f"  Keystroke delay: {delay:.3f}s")

    print("\nBezier curve test:")
    points = human.bezier_curve((0, 0), (100, 100), 5)
    for p in points:
        print(f"  Point: {p}")
