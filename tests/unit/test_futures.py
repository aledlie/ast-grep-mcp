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


class TestTimedOutPendingFutureCancellation:
    """A queued item whose wait timed out must never execute later (CR-06)."""

    def test_timed_out_queued_item_never_runs_after_worker_frees(self):
        release = threading.Event()
        executed = []
        results = {}
        errors = {}

        def func(item):
            executed.append(item)
            if item == "hung":
                release.wait(timeout=HUNG_WORKER_SAFETY_NET_SECONDS)
            return item

        def on_error(item, error):
            errors[item] = error
            if item == "queued":
                # Free the hung worker while the loop is still waiting on
                # "last". Pre-fix, the freed worker dequeued and ran "queued"
                # even though it was already reported as timed out; post-fix
                # "queued" was cancelled before this callback ran.
                release.set()

        try:
            map_with_per_item_timeout(
                ["hung", "queued", "last"],
                func,
                timeout_seconds=TIMEOUT_SECONDS,
                max_workers=1,
                on_success=lambda item, result: results.__setitem__(item, result),
                on_error=on_error,
            )
        finally:
            release.set()

        assert "queued" not in executed, "timed-out queued item must not run after a worker frees"
        assert isinstance(errors["hung"], TimeoutError)
        assert isinstance(errors["queued"], TimeoutError)


TOTAL_TIMEOUT_SECONDS = 1.5
HUNG_WORKER_TOTAL_SAFETY_NET_SECONDS = 30


class TestMapWithTotalTimeout:
    """Tests for the shared total_timeout_seconds deadline (CR-05 / CR-26)."""

    def test_fast_items_complete_within_total_deadline(self):
        """Items that finish quickly are unaffected by a generous total deadline."""
        results = {}
        errors = {}

        map_with_per_item_timeout(
            ["a", "b", "c"],
            lambda item: item.upper(),
            timeout_seconds=TIMEOUT_SECONDS,
            max_workers=2,
            on_success=lambda item, result: results.__setitem__(item, result),
            on_error=lambda item, error: errors.__setitem__(item, error),
            total_timeout_seconds=TOTAL_TIMEOUT_SECONDS,
        )

        assert results == {"a": "A", "b": "B", "c": "C"}
        assert errors == {}

    def test_total_deadline_caps_wall_clock_below_n_times_per_item(self):
        """With N hung workers, total wall-clock must stay near total_timeout_seconds, not N×timeout."""
        release = threading.Event()
        errors = {}

        # 5 items, 1 worker → serial waits; per-item=5s → worst case 25s without total deadline
        n_items = 5
        per_item_timeout = 5.0
        total_timeout = 2.0  # must return in ~2s, not ~25s

        try:
            start = time.monotonic()
            map_with_per_item_timeout(
                [f"h{i}" for i in range(n_items)],
                lambda item: release.wait(timeout=HUNG_WORKER_TOTAL_SAFETY_NET_SECONDS),
                timeout_seconds=per_item_timeout,
                max_workers=1,
                on_success=lambda item, result: None,
                on_error=lambda item, error: errors.__setitem__(item, error),
                total_timeout_seconds=total_timeout,
            )
            elapsed = time.monotonic() - start
        finally:
            release.set()

        assert elapsed < per_item_timeout, f"should return in ~{total_timeout}s, took {elapsed:.2f}s"
        assert len(errors) == n_items
        assert all(isinstance(e, TimeoutError) for e in errors.values())

    def test_expired_deadline_marks_remaining_items_without_waiting(self):
        """Items past the deadline are reported immediately as TimeoutError."""
        errors = {}
        processed = []

        # Simulate: first item takes 0.5s (just under total_timeout=0.3s, so deadline expires)
        # remaining items should be marked without waiting
        def func(item):
            if item == "slow":
                time.sleep(0.5)
            return item

        start = time.monotonic()
        map_with_per_item_timeout(
            ["slow", "after_deadline"],
            func,
            timeout_seconds=10.0,
            max_workers=1,
            on_success=lambda item, result: processed.append(item),
            on_error=lambda item, error: errors.__setitem__(item, error),
            total_timeout_seconds=0.3,
        )
        elapsed = time.monotonic() - start

        # Should have returned quickly (not waited 10s for after_deadline)
        assert elapsed < 2.0, f"should return promptly, took {elapsed:.2f}s"
        assert "after_deadline" in errors
        assert isinstance(errors["after_deadline"], TimeoutError)
