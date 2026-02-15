"""
Synchronous execution utilities.
"""

import asyncio
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine synchronously.

    Works both when there's an existing event loop and when there isn't.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # Already in an async context - run in a new thread
        import concurrent.futures
        import threading

        result: T | None = None
        exception: Exception | None = None

        def run_in_thread() -> None:
            nonlocal result, exception
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            except Exception as e:
                exception = e

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()

        if exception:
            raise exception
        return result  # type: ignore

    else:
        # No event loop - create one
        return asyncio.run(coro)


def make_sync(async_func: Any) -> Any:
    """
    Decorator to create a synchronous version of an async function.

    Usage:
        @make_sync
        async def my_async_func():
            ...

        # Now my_async_func.sync() is available
    """
    import functools

    @functools.wraps(async_func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        return run_sync(async_func(*args, **kwargs))

    async_func.sync = sync_wrapper
    return async_func
