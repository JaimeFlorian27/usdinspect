"""Defines the entrypoint for the tool."""

from pathlib import Path

from pxr.Usd import Stage

from .app import UsdInspectApp


def run() -> None:
    """Run the application."""
    kitchen_set_file = (
        Path(__file__).parent.parent.parent.parent
        / "data"
        / "usd"
        / "Kitchen_set"
        / "Kitchen_set.usd"
    )
    stage = Stage.Open(str(kitchen_set_file))
    app = UsdInspectApp(stage)
    app.run()
