"""Unit tests for utils.futures.map_with_per_item_timeout.

The shared helper owns the corrected wait lifecycle (per-item
future.result(timeout=...) + shutdown(wait=False, cancel_futures=True))
adopted by deduplication enrichment, batch coverage, and cross-language
search.
"""

import threading
import time

from ast_grep_mcp.utils.futures import map_with_per_item_timeout

TIMEOUT_SECONDS = 1
PROMPT_RETURN_BOUND_SECONDS = 10
HUNG_WORKER_SAFETY_NET_SECONDS = 30


class TestMapWithPerItemTimeout:
    def test_success_results_delivered_per_item(self):
        results = {}
        errors = {}

        map_with_per_item_timeout(
            ["a", "b", "c"],
            lambda item: item.upper(),
            timeout_seconds=TIMEOUT_SECONDS,
            max_workers=2,
            on_success=lambda item, result: results.__setitem__(item, result),
            on_error=lambda item, error: errors.__setitem__(item, error),
        )

        assert results == {"a": "A", "b": "B", "c": "C"}
        assert errors == {}

    def test_worker_exception_routed_to_on_error(self):
        results = {}
        errors = {}

        def func(item):
            if item == "bad":
                raise ValueError("boom")
            return item

        map_with_per_item_timeout(
            ["ok", "bad"],
            func,
            timeout_seconds=TIMEOUT_SECONDS,
            max_workers=2,
            on_success=lambda item, result: results.__setitem__(item, result),
            on_error=lambda item, error: errors.__setitem__(item, error),
        )

        assert results == {"ok": "ok"}
        assert isinstance(errors["bad"], ValueError)
        assert str(errors["bad"]) == "boom"

    def test_hung_worker_times_out_without_blocking_return(self):
        release = threading.Event()
        results = {}
        errors = {}

        def func(item):
            if item == "hung":
                release.wait(timeout=HUNG_WORKER_SAFETY_NET_SECONDS)
            return item

        try:
            start = time.monotonic()
            map_with_per_item_timeout(
                ["hung", "fast"],
                func,
                timeout_seconds=TIMEOUT_SECONDS,
                max_workers=2,
                on_success=lambda item, result: results.__setitem__(item, result),
                on_error=lambda item, error: errors.__setitem__(item, error),
            )
            elapsed = time.monotonic() - start
        finally:
            release.set()

        assert elapsed < PROMPT_RETURN_BOUND_SECONDS, f"helper should return promptly, took {elapsed:.1f}s"
        assert isinstance(errors["hung"], TimeoutError)
        assert results == {"fast": "fast"}

    def test_item_starved_behind_hung_workers_reported_as_error(self):
        release = threading.Event()
        errors = {}

        def func(item):
            release.wait(timeout=HUNG_WORKER_SAFETY_NET_SECONDS)

        try:
            map_with_per_item_timeout(
                ["h1", "h2", "starved"],
                func,
                timeout_seconds=TIMEOUT_SECONDS,
                max_workers=2,
                on_success=lambda item, result: None,
                on_error=lambda item, error: errors.__setitem__(item, error),
            )
        finally:
            release.set()

        assert set(errors) == {"h1", "h2", "starved"}
        assert all(isinstance(error, TimeoutError) for error in errors.values())

    def test_empty_items_is_a_no_op(self):
        map_with_per_item_timeout(
            [],
            lambda item: item,
            timeout_seconds=TIMEOUT_SECONDS,
            max_workers=1,
            on_success=lambda item, result: (_ for _ in ()).throw(AssertionError("unexpected success callback")),
            on_error=lambda item, error: (_ for _ in ()).throw(AssertionError("unexpected error callback")),
        )

    def test_callbacks_run_on_calling_thread(self):
        calling_thread = threading.current_thread()
        callback_threads = []

        map_with_per_item_timeout(
            ["a", "b"],
            lambda item: item,
            timeout_seconds=TIMEOUT_SECONDS,
            max_workers=2,
            on_success=lambda item, result: callback_threads.append(threading.current_thread()),
            on_error=lambda item, error: callback_threads.append(threading.current_thread()),
        )

        assert callback_threads and all(thread is calling_thread for thread in callback_threads)
