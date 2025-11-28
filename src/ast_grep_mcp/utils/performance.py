"""Performance monitoring utilities for MCP tools.

This module provides decorators and utilities for monitoring
tool execution time, logging performance metrics, and tracking
slow operations.
"""
import time
from functools import wraps
from typing import Any, Callable, TypeVar

import sentry_sdk

from ast_grep_mcp.core.logging import get_logger

# Type variable for generic function decorators
F = TypeVar('F', bound=Callable[..., Any])


def monitor_performance(func: F) -> F:
    """Decorator to monitor tool performance and log metrics.

    Measures execution time and logs:
    - Success: tool name, duration_ms, status="success"
    - Failure: tool name, duration_ms, status="failed", error message

    Also sends performance spans to Sentry for monitoring.

    Usage:
        @monitor_performance
        def my_tool_function(...):
            ...

    Args:
        func: Function to monitor

    Returns:
        Wrapped function with performance monitoring
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(f"performance.{func.__name__}")
        start_time = time.time()

        # Create Sentry performance span
        with sentry_sdk.start_span(
            op="tool.execution",
            name=func.__name__
        ) as span:
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Log success
                logger.info(
                    "tool_performance",
                    tool=func.__name__,
                    duration_ms=duration_ms,
                    status="success"
                )

                # Add span data
                span.set_data("duration_ms", duration_ms)
                span.set_data("status", "success")

                # Warn if slow (>5 seconds)
                if duration_ms > 5000:
                    logger.warning(
                        "slow_tool_execution",
                        tool=func.__name__,
                        duration_ms=duration_ms
                    )

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                # Log failure
                logger.error(
                    "tool_performance",
                    tool=func.__name__,
                    duration_ms=duration_ms,
                    status="failed",
                    error=str(e)[:200]
                )

                # Add span data
                span.set_data("duration_ms", duration_ms)
                span.set_data("status", "failed")
                span.set_data("error", str(e)[:200])

                # Re-raise to preserve exception behavior
                raise

    return wrapper  # type: ignore


def monitor_performance_async(func: F) -> F:
    """Decorator to monitor async tool performance and log metrics.

    Async version of monitor_performance decorator.

    Usage:
        @monitor_performance_async
        async def my_async_tool(...):
            ...

    Args:
        func: Async function to monitor

    Returns:
        Wrapped async function with performance monitoring
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(f"performance.{func.__name__}")
        start_time = time.time()

        # Create Sentry performance span
        with sentry_sdk.start_span(
            op="tool.execution.async",
            name=func.__name__
        ) as span:
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Log success
                logger.info(
                    "tool_performance",
                    tool=func.__name__,
                    duration_ms=duration_ms,
                    status="success",
                    async_execution=True
                )

                # Add span data
                span.set_data("duration_ms", duration_ms)
                span.set_data("status", "success")
                span.set_data("async", True)

                # Warn if slow (>5 seconds)
                if duration_ms > 5000:
                    logger.warning(
                        "slow_tool_execution",
                        tool=func.__name__,
                        duration_ms=duration_ms,
                        async_execution=True
                    )

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                # Log failure
                logger.error(
                    "tool_performance",
                    tool=func.__name__,
                    duration_ms=duration_ms,
                    status="failed",
                    error=str(e)[:200],
                    async_execution=True
                )

                # Add span data
                span.set_data("duration_ms", duration_ms)
                span.set_data("status", "failed")
                span.set_data("error", str(e)[:200])
                span.set_data("async", True)

                # Re-raise to preserve exception behavior
                raise

    return wrapper  # type: ignore


class PerformanceTimer:
    """Context manager for timing code blocks.

    Usage:
        with PerformanceTimer("operation_name") as timer:
            # Code to time
            ...

        print(f"Elapsed: {timer.elapsed_ms}ms")
    """

    def __init__(self, operation_name: str, log_on_exit: bool = True):
        """Initialize performance timer.

        Args:
            operation_name: Name of the operation being timed
            log_on_exit: Whether to log elapsed time on exit
        """
        self.operation_name = operation_name
        self.log_on_exit = log_on_exit
        self.logger = get_logger("performance.timer")
        self.start_time: float = 0
        self.end_time: float = 0

    def __enter__(self) -> "PerformanceTimer":
        """Start the timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop the timer and optionally log results."""
        self.end_time = time.time()

        if self.log_on_exit:
            status = "failed" if exc_type else "success"
            self.logger.info(
                "operation_timing",
                operation=self.operation_name,
                duration_ms=self.elapsed_ms,
                status=status
            )

    @property
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.end_time == 0:
            # Timer still running
            return int((time.time() - self.start_time) * 1000)
        return int((self.end_time - self.start_time) * 1000)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.elapsed_ms / 1000.0


def track_slow_operations(threshold_ms: int = 1000) -> Callable[[F], F]:
    """Decorator factory to track operations exceeding a time threshold.

    Usage:
        @track_slow_operations(threshold_ms=500)
        def my_function(...):
            ...

    Args:
        threshold_ms: Threshold in milliseconds for logging slow operations

    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger("performance.slow_ops")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                if duration_ms > threshold_ms:
                    logger.warning(
                        "slow_operation_detected",
                        operation=func.__name__,
                        duration_ms=duration_ms,
                        threshold_ms=threshold_ms,
                        slowdown_factor=round(duration_ms / threshold_ms, 2)
                    )

                return result

            except Exception:
                # Still track duration even on error
                duration_ms = int((time.time() - start_time) * 1000)
                if duration_ms > threshold_ms:
                    logger.warning(
                        "slow_operation_detected",
                        operation=func.__name__,
                        duration_ms=duration_ms,
                        threshold_ms=threshold_ms,
                        status="failed"
                    )
                raise

        return wrapper  # type: ignore

    return decorator
