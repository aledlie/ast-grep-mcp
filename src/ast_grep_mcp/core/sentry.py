"""Sentry error tracking integration for ast-grep MCP server."""
import os
from typing import Any
import sentry_sdk
from sentry_sdk.integrations.anthropic import AnthropicIntegration
from ast_grep_mcp.core.logging import get_logger

# Re-export capture_exception for backward compatibility
from sentry_sdk import capture_exception


def init_sentry(service_name: str = "ast-grep-mcp") -> None:
    """Initialize Sentry with Anthropic AI integration and service tagging.

    Args:
        service_name: Unique service identifier (default: 'ast-grep-mcp')
    """
    def _tag_event(event: Any, hint: Any) -> Any:
        """Add service tags to every event for unified project."""
        event.setdefault("tags", {})
        event["tags"]["service"] = service_name
        event["tags"]["language"] = "python"
        event["tags"]["component"] = "mcp-server"
        return event

    # Only initialize if SENTRY_DSN is set
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        # Environment
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        # Integrations - Include Anthropic AI
        integrations=[
            AnthropicIntegration(
                include_prompts=True,  # Capture prompts and responses
            ),
        ],
        # Performance monitoring - REQUIRED for AI tracking
        traces_sample_rate=1.0 if os.getenv("SENTRY_ENVIRONMENT") == "development" else 0.1,
        profiles_sample_rate=1.0 if os.getenv("SENTRY_ENVIRONMENT") == "development" else 0.1,
        # Send PII for AI context
        send_default_pii=True,
        # Additional options
        attach_stacktrace=True,
        max_breadcrumbs=50,
        debug=os.getenv("SENTRY_ENVIRONMENT") == "development",
        # Tag every event with service name
        before_send=_tag_event,
    )

    # Set global tags for all future events
    sentry_sdk.set_tag("service", service_name)
    sentry_sdk.set_tag("language", "python")
    sentry_sdk.set_tag("component", "mcp-server")

    logger = get_logger("sentry")
    logger.info(
        "sentry_initialized",
        service=service_name,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
    )