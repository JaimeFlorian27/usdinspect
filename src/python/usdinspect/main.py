"""Defines the entrypoint for the tool."""
from pxr.Usd import Stage

from .app import UsdInspectApp


def run() -> None:
    """Run the application."""
    stage = Stage.Open("/Users/yunzhang/Downloads/Kitchen_set/Kitchen_set.usd")
    app = UsdInspectApp(stage)
    app.run()
