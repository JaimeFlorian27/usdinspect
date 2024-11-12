"""Module that defines the application class."""

from pathlib import Path

from pxr.Usd import Stage
from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll
from textual.widgets import Footer, Header, TabbedContent, Tree

from .widgets import AttributeValuesTable, PrimAttributesTable, StageTree


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
        self._prim_attributes_table = PrimAttributesTable()
        self._prim_attribute_values_table = AttributeValuesTable(
            id="attribute_values_table",
        )

    def compose(self) -> ComposeResult:
        """Build the UI.

        Yields:
            ComposeResult.

        """
        yield Header()
        self._stage_tree.populate(self._stage)
        self._stage_tree.focus()
        with HorizontalScroll():
            yield self._stage_tree

        with HorizontalScroll():
            with TabbedContent("Attributes"):
                yield self._prim_attributes_table
            yield self._prim_attribute_values_table
        yield Footer()

    @on(StageTree.NodeHighlighted, "StageTree")
    def stage_tree_node_highlighted(self, event: StageTree.NodeHighlighted) -> None:
        """Handle the selection of a prim node in the tree.

        populate any widgets whose data depend on the currently selected prim.

        """
        if not event.node.data:
            return
        prim = self._stage.GetPrimAtPath(event.node.data)

        # Update the properties table
        self._prim_attributes_table.populate(prim)

    @on(PrimAttributesTable.RowHighlighted, "PrimAttributesTable")
    def populate_attribute_values(
        self,
        event: PrimAttributesTable.RowHighlighted,
    ) -> None:
        """Handle the selection of a prim attribute.

        populate any widgets whose data depend on the currently selected prim.

        """
        selected_prim_node = self._stage_tree.cursor_node
        if not selected_prim_node:
            return

        prim = self._stage.GetPrimAtPath(str(selected_prim_node.data))
        attribute = prim.GetAttribute(str(event.row_key.value))

        self._prim_attribute_values_table.populate(attribute)
