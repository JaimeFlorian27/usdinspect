"""Module that defines the application class."""

from pathlib import Path
from typing import TYPE_CHECKING

from pxr import Sdf, Usd
from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll
from textual.widgets import Footer, Header, TabbedContent

from .widgets import (
    MetadataTable,
    PrimLayerStackTable,
    PrimPropertiesTable,
    PropertyValuesTable,
    StageTree,
)

if TYPE_CHECKING:
    from pxr.Sdf import PrimSpec


class UsdInspectApp(App):
    """Usd Inspect main application class."""

    CSS_PATH = Path(__file__).parent / "ui" / "style.tcss"

    def __init__(self, stage: Usd.Stage) -> None:
        """Construct a Usd Inspect application instance.

        Args:
            stage: Usd Stage to inspect.

        """
        super().__init__()
        self._stage = stage
        self._stage_tree = StageTree("Root", "/", classes="bordered_widget")
        self._prim_composition_list = PrimLayerStackTable(classes="bordered_widget")
        self._prim_properties_table = PrimPropertiesTable()
        self._property_values_table = PropertyValuesTable()
        self._prim_metadata_table = MetadataTable()
        self._property_metatada_table = MetadataTable()

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

        with HorizontalScroll(can_focus=False):
            # Tabs for the Prim Data.
            with TabbedContent(
                "Properties",
                "Metadata",
                classes="bordered_widget",
            ) as tabs:
                tabs.border_title = "Prim Data"
                yield self._prim_properties_table
                yield self._prim_metadata_table

            # Tabs for the Property data.
            with TabbedContent(
                "Values",
                "Metadata",
                classes="bordered_widget",
            ) as tabs:
                tabs.border_title = "Property Data"
                yield self._property_values_table
                yield self._property_metatada_table
        yield Footer()

    @on(StageTree.NodeHighlighted, "StageTree")
    def _stage_tree_node_highlighted(self, event: StageTree.NodeHighlighted) -> None:
        """Handle the selection of a prim node in the tree.

        Populate any widgets whose data depend on the currently selected prim.

        """
        if not event.node.data:
            return
        prim = self._stage.GetPrimAtPath(event.node.data)

        # Update the widgets that depend on the selected prim.
        self._prim_properties_table.prim = prim
        self._prim_composition_list.prim = prim

    @on(PrimPropertiesTable.RowHighlighted, "PrimPropertiesTable")
    def _property_highlighted(
        self,
        event: PrimPropertiesTable.RowHighlighted,
    ) -> None:
        """Handle the selection of a prim property.

        Populate any widgets whose data depend on the currently selected property.

        """
        selected_prim_node = self._stage_tree.cursor_node
        if not selected_prim_node:
            return

        prim = self._stage.GetPrimAtPath(str(selected_prim_node.data))
        prim_property = prim.GetProperty(str(event.row_key.value))

        self._property_values_table.property = prim_property
        self._property_metatada_table.usd_object = prim_property

    @on(PrimLayerStackTable.RowHighlighted, "PrimLayerStackTable")
    def _layer_highlighted(
        self,
        event: PrimLayerStackTable.RowHighlighted,
    ) -> None:
        """Handle the selection of a layer that contributes to the current prim.

        Populate any widgets whose data depend on the currently selected layer.

        """
        row_key: str | None = event.row_key.value
        if not row_key:
            return

        # Handle composed case, get the currently selected prim and assign it to
        # the properties table prim attr. I do this way as the reactive prim property
        # will always update the properties table when assigned.
        if row_key == "composed":
            selected_prim_node = self._stage_tree.cursor_node
            if not selected_prim_node:
                return

            selected_prim = self._stage.GetPrimAtPath(str(selected_prim_node.data))
            self._prim_properties_table.prim = selected_prim
            self._prim_metadata_table.usd_object = selected_prim
            return

        # Regular case, get the prim spec from the selected layer and assign it to the
        # properties table.
        layer_path, prim_spec_path = row_key.split("|")
        prim_spec: PrimSpec | None = Sdf.Layer.FindOrOpen(layer_path).GetPrimAtPath(
            prim_spec_path,
        )

        self._prim_properties_table.prim = prim_spec
        self._prim_metadata_table.sdf_spec_object = prim_spec
        return
