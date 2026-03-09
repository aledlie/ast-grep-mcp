"""Shared context managers for MCP tool error handling, timing, and Sentry capture."""

import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator

import sentry_sdk

from ast_grep_mcp.constants import DisplayDefaults, FormattingDefaults
from ast_grep_mcp.core.logging import get_logger


def _handle_tool_error(
    tool_name: str, start_time: float, e: Exception, sentry_extras: dict[str, Any], *, logger: Any = None
) -> None:
    """Log error and capture to Sentry for a failed tool invocation."""
    execution_time = time.time() - start_time
    if logger is None:
        logger = get_logger(f"tool.{tool_name}")
    logger.error(
        "tool_failed",
        tool=tool_name,
        status="failed",
        execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
        error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
    )
    sentry_sdk.capture_exception(
        e,
        extras={
            "tool": tool_name,
            **sentry_extras,
            "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
        },
    )


@contextmanager
def tool_context(tool_name: str, **sentry_extras: Any) -> Generator[float, None, None]:
    """Context manager for tool error handling, timing, and Sentry capture.

    Yields the start_time so callers can compute execution_time for success logging.
    On exception: logs error, captures to Sentry, and re-raises.

    Usage::

        with tool_context("my_tool", project_folder=folder) as start_time:
            result = do_work()
            elapsed = round(time.time() - start_time, FormattingDefaults.ROUNDING_PRECISION)
            logger.info("tool_completed", tool="my_tool", execution_time_seconds=elapsed)
            return result
    """
    start_time = time.time()
    try:
        yield start_time
    except Exception as e:
        _handle_tool_error(tool_name, start_time, e, sentry_extras)
        raise


@asynccontextmanager
async def async_tool_context(tool_name: str, **sentry_extras: Any) -> AsyncGenerator[float, None]:
    """Async context manager for tool error handling, timing, and Sentry capture.

    Identical to tool_context but for use with ``async with``.

    Usage::

        async with async_tool_context("my_tool", type_name=name) as start_time:
            result = await do_async_work()
            elapsed = round(time.time() - start_time, FormattingDefaults.ROUNDING_PRECISION)
            logger.info("tool_completed", tool="my_tool", execution_time_seconds=elapsed)
            return result
    """
    start_time = time.time()
    try:
        yield start_time
    except Exception as e:
        _handle_tool_error(tool_name, start_time, e, sentry_extras)
        raise
