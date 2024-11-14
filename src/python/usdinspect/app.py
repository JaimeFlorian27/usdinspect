"""Module that defines the application class."""

from pathlib import Path
from typing import TYPE_CHECKING

from pxr.Usd import Stage
from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll
from textual.widgets import Footer, Header, TabbedContent

from .widgets import (
    AttributeValuesTable,
    PrimAttributesTable,
    PrimCompositionList,
    StageTree,
)

if TYPE_CHECKING:
    from pxr.Sdf import PrimSpec


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
        self._stage_tree = StageTree("Root", "/")
        self._prim_attributes_table = PrimAttributesTable()
        self._prim_attribute_values_table = AttributeValuesTable()
        self._prim_composition_list = PrimCompositionList()

    def compose(self) -> ComposeResult:
        """Build the UI.

        Yields:
            ComposeResult.

        """
        yield Header()
        self._stage_tree.stage = self._stage
        self._stage_tree.focus()
        with HorizontalScroll():
            yield self._stage_tree
            yield self._prim_composition_list

        with HorizontalScroll():
            with TabbedContent("Attributes") as tabs:
                tabs.border_title = "Prim Data"
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

        # Update the widgets that depend on the selected prim.
        self._prim_attributes_table.prim = prim
        self._prim_composition_list.prim = prim

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

        self._prim_attribute_values_table.attribute = attribute

    @on(PrimCompositionList.Highlighted, "PrimCompositionList")
    def layer_highlighted(
        self,
        event: PrimCompositionList.Highlighted,
    ) -> None:
        """Handle the selection of a prim attribute.

        populate any widgets whose data depend on the currently selected prim.

        """
        prim_spec: PrimSpec | None = event.prim_spec

        # If no prim spec assume that we are targeting the composed prim.
        if not prim_spec:
            selected_prim_node = self._stage_tree.cursor_node
            if not selected_prim_node:
                return

            selected_prim = self._stage.GetPrimAtPath(str(selected_prim_node.data))
            self._prim_attributes_table.prim = selected_prim
            return

        self._prim_attributes_table.prim_spec = prim_spec
        return
