"""Module that defines the application class."""

from pathlib import Path

from pxr.Usd import Stage
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll
from textual.widgets import DataTable, Footer, Header, Placeholder, TabbedContent, Tree

from .widgets import StageTree


class UsdInspectApp(App):
    """Usd Inspect main application class."""

    CSS_PATH = Path(__file__).parent / "ui" / "style.tcss"

    def __init__(self, stage: Stage) -> None:
        """Construct a Usd Inspect application instance.

        Args:
            stage: Usd Stage to inspect.

        """
        super().__init__()
        self._stage = stage
        self._stage_tree = StageTree("/")
        self._prim_attributes_table = DataTable()

    def compose(self) -> ComposeResult:
        """Build the UI.

        Yields:
            ComposeResult.

        """
        yield Header()
        self._stage_tree.populate(self._stage)
        with HorizontalScroll():
            yield self._stage_tree
            yield Placeholder("Placeholder Composition view")

        self._prim_attributes_table.add_columns("Type", "Property Name")
        with HorizontalScroll():
            with TabbedContent("Attributes", "Metadata"):
                yield self._prim_attributes_table
                yield Placeholder("Placeholder Metadata table")
            yield Placeholder("Placeholder Value view widget")
        yield Footer()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle the selection of a prim node in the tree.

        populate any widgets whose data depend on the currently selected prim.

        """
        if not event.node.data:
            return
        prim = self._stage.GetPrimAtPath(event.node.data)

        self._prim_attributes_table.clear()
        for attribute in prim.GetAttributes():
            self._prim_attributes_table.add_row(
                attribute.GetTypeName(),
                attribute.GetName(),
            )
