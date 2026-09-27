"""Logging setup shared by the FastAPI application and scripts."""

import logging


def configure_logging(level: str) -> None:
    """Configure concise, structured-enough application logging."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
