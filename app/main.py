"""Uvicorn entrypoint."""

from __future__ import annotations

import logging
import uvicorn

from app import config


class HealthCheckFilter(logging.Filter):
    """Filter out GET /health HTTP 200 log entries from Uvicorn access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "uvicorn.access":
            return True
        msg = record.getMessage()
        return not ("GET /health" in msg and " 200" in msg)


def main() -> None:
    # Apply filter to uvicorn access logger
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.addFilter(HealthCheckFilter())

    uvicorn.run(
        "app.api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()

