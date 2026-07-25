"""ThreadPoolExecutor helper enforcing per-item timeouts.

The corrected wait lifecycle lives here once, shared by deduplication
enrichment, batch test-coverage checks, and cross-language search:

- Wait on each future directly with ``future.result(timeout=...)`` —
  ``as_completed()`` without a timeout only yields finished futures, which
  makes a per-item timeout unreachable and lets one hung worker block forever.
- Never use the executor as a context manager: ``__exit__`` calls
  ``shutdown(wait=True)``, which blocks on hung workers even after their items
  timed out. Shut down with ``wait=False, cancel_futures=True`` instead, so
  hung workers are abandoned and queued work that never started is dropped.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Dict, Sequence, TypeVar

ItemT = TypeVar("ItemT")
ResultT = TypeVar("ResultT")


def map_with_per_item_timeout(
    items: Sequence[ItemT],
    func: Callable[[ItemT], ResultT],
    *,
    timeout_seconds: float,
    max_workers: int,
    on_success: Callable[[ItemT, ResultT], None],
    on_error: Callable[[ItemT, Exception], None],
) -> None:
    """Run ``func`` over ``items`` in a fresh thread pool, bounding each wait.

    Waits happen in submission order, each bounded by ``timeout_seconds``
    measured from when the wait loop reaches that item's future — so total
    wall clock is up to ``len(items) * timeout_seconds`` when everything
    hangs, and an item queued behind hung workers is reported as timed out
    even though it never ran.

    A worker that outlives its timeout is abandoned: it keeps running but its
    result is discarded. ``func`` therefore must not mutate state the caller
    reads after this returns — hand workers private copies and merge results
    in ``on_success``. Abandoned workers keep their (non-daemon) thread until
    they finish, so a worker that never finishes blocks interpreter exit.

    Callbacks must not raise: a raising callback aborts the wait loop, skipping
    callbacks for every remaining item (the pool is still shut down without
    blocking).

    Args:
        items: Work items, one future each.
        func: Called as ``func(item)`` on a worker thread.
        timeout_seconds: Maximum seconds to wait for each item's result.
        max_workers: Thread pool size for this call.
        on_success: Called on the calling thread with ``(item, result)`` for
            each item completing within its wait window.
        on_error: Called on the calling thread with ``(item, exception)`` when
            the wait timed out (a ``TimeoutError``) or ``func`` raised.
    """
    if not items:
        return

    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        futures: Dict[Future[ResultT], ItemT] = {executor.submit(func, item): item for item in items}
        for future, item in futures.items():
            try:
                result = future.result(timeout=timeout_seconds)
            except Exception as error:
                on_error(item, error)
            else:
                on_success(item, result)
    finally:
        # Threads cannot be killed; abandon hung workers rather than blocking
        # the caller, and cancel queued work that never started.
        executor.shutdown(wait=False, cancel_futures=True)
