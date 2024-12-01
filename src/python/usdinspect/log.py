"""Contains all the conde related to setting up and retrieving the app's Logger."""
import logging
import logging.config

from rich.logging import RichHandler

FORMAT = "%(message)s"


def get() -> logging.Logger:
    """Get the application's main Logger.

    Returns:
        UsdInspect's Logger.

    """
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()],
    )
    return logging.getLogger("usdinspect")
