"""
Basic Weber SDK Usage Examples.

This demonstrates the fundamental patterns for using the SDK.
"""

import asyncio
from weber_sdk import Weber


async def async_example():
    """Async usage pattern (recommended)."""
    async with Weber() as w:
        # List available servers
        print("Available servers:", w.list_servers())

        # Voice example
        await w.voice.speak("Hello, Weber SDK is working!")

        # Excel example (requires Excel to be running on Windows)
        status = await w.excel.get_status()
        print("Excel status:", status)


def sync_example():
    """Synchronous usage pattern."""
    from weber_sdk.utils import run_sync

    w = Weber()

    # Use sync versions of methods
    servers = w.list_servers()
    print("Available servers:", servers)

    # Note: Most operations are async, use run_sync for sync contexts
    async def speak():
        await w.voice.speak("Hello from sync context!")

    run_sync(speak())


if __name__ == "__main__":
    print("=== Async Example ===")
    asyncio.run(async_example())

    print("\n=== Sync Example ===")
    sync_example()
