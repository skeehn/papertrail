import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging() -> None:
    """Setup structured logging configuration"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if settings.ENVIRONMENT == "production"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Set log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


def log_request(request_id: str, method: str, url: str, **kwargs) -> None:
    """Log HTTP request details"""
    logger = get_logger("http.request")
    logger.info("HTTP request", request_id=request_id, method=method, url=url, **kwargs)


def log_response(
    request_id: str, status_code: int, response_time: float, **kwargs
) -> None:
    """Log HTTP response details"""
    logger = get_logger("http.response")
    logger.info(
        "HTTP response",
        request_id=request_id,
        status_code=status_code,
        response_time=response_time,
        **kwargs
    )


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """Log error with context"""
    logger = get_logger("error")
    logger.error(
        "Application error",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        exc_info=True,
    )


def log_agent_activity(agent_name: str, action: str, **kwargs) -> None:
    """Log agent activity"""
    logger = get_logger("agent")
    logger.info("Agent activity", agent_name=agent_name, action=action, **kwargs)


def log_graph_operation(operation: str, node_count: int = None, **kwargs) -> None:
    """Log graph database operations"""
    logger = get_logger("graph")
    logger.info("Graph operation", operation=operation, node_count=node_count, **kwargs)


def log_processing_step(step: str, file_id: str = None, **kwargs) -> None:
    """Log PDF processing steps"""
    logger = get_logger("processing")
    logger.info("Processing step", step=step, file_id=file_id, **kwargs)
