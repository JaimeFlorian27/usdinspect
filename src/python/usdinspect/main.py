"""Defines the entrypoint for the tool."""

import argparse
from pathlib import Path

from pxr.Usd import Stage

from . import log
from .app import UsdInspectApp


def construct_args_parser() -> argparse.ArgumentParser:
    """Construct an Argument Parser.

    Returns:
        Constructed ArgumentParser instance.

    """
    parser = argparse.ArgumentParser(prog="Usd Inspect")

    parser.add_argument("filename")

    parser.parse_args()
    return parser


def run() -> None:
    """Run the application."""
    parser = construct_args_parser()

    args = parser.parse_args()
    logger = log.get()

    filename: Path = Path(args.filename)

    if not filename.exists():
        logger.error("The file does not exist.")
        return

    stage = Stage.Open(str(filename))
    app = UsdInspectApp(stage)
    app.run()
