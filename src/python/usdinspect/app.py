"""Module that defines the application class."""

from pathlib import Path
from typing import TYPE_CHECKING

from pxr import Sdf, Usd
from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll
from textual.widgets import Footer, Header, TabbedContent

from . import values_table
from .widgets import (
    MetadataTable,
    PrimDataTabs,
    PrimLayerStackTable,
    PrimPropertiesTable,
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
        self._property_values_table = values_table.ValuesTable()
        self._property_metatada_table = MetadataTable()
        self._value_tabs = TabbedContent(
            "Values",
            "Metadata",
            classes="bordered_widget",
        )

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
            yield PrimDataTabs(id="prim_data_tabs", classes="bordered_widget")
            with self._value_tabs:
                self._value_tabs.border_title = "Property Dataaaaaa"
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
            self._property_values_table.state = values_table.NoValueDisplayState()
            return

        # If the table is empty and the message is emitted the RowKey will be None
        if not event.row_key:
            self._property_values_table.state = values_table.NoValueDisplayState()
            return

        prim = self._stage.GetPrimAtPath(str(selected_prim_node.data))
        prim_property = prim.GetProperty(str(event.row_key.value))

        self._property_values_table.state = values_table.PropertyValueDisplayState(
            prim_property,
        )
        self._property_metatada_table.data_object = prim_property

    @on(MetadataTable.RowHighlighted, "#prim_metadata_table")
    def _prim_metadatum_highlighted(
        self,
        event: MetadataTable.RowHighlighted,
    ) -> None:
        if not event.row_key:
            self._property_values_table.state = values_table.NoValueDisplayState()
            return

        metadata_value = event.data_table.get_cell(event.row_key, "value")
        self._property_values_table.state = values_table.MetadatumValueDisplayState(
            metadata_value,
        )

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

        prim_data_tabs = self.query_one("#prim_data_tabs", PrimDataTabs)
        # Handle composed case, get the currently selected prim and assign it to
        # the properties table prim attr. I do this way as the reactive prim property
        # will always update the properties table when assigned.
        if row_key == "composed":
            selected_prim_node = self._stage_tree.cursor_node
            if not selected_prim_node:
                return

            selected_prim = self._stage.GetPrimAtPath(str(selected_prim_node.data))
            prim_data_tabs.prim = selected_prim
            return

        # Regular case, get the prim spec from the selected layer and assign it to the
        # properties table.
        layer_path, prim_spec_path = row_key.split("|")
        prim_spec: PrimSpec | None = Sdf.Layer.FindOrOpen(layer_path).GetPrimAtPath(
            prim_spec_path,
        )

        prim_data_tabs.prim = prim_spec
        return

    @on(TabbedContent.TabActivated, "#prim_data_tabs")
    def _prim_data_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab changes in the Prim data Tabs."""
        if str(event.tab.label) == "Properties":
            self._value_tabs.border_title = "Property Data"
            self._value_tabs.show_tab("tab-2")

        if str(event.tab.label) == "Metadata":
            self._value_tabs.hide_tab("tab-2")
            self._value_tabs.border_title = "Metadatum data"
