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
    Timeline,
    ValueDataTabs,
)

if TYPE_CHECKING:
    from pxr.Sdf import PrimSpec


class UsdInspectApp(App):
    """Usd Inspect main application class."""

    TITLE = " USD Inspect"
    CSS_PATH = Path(__file__).parent / "ui" / "style.tcss"

    def __init__(self, stage: Usd.Stage) -> None:
        """Construct a Usd Inspect application instance.

        Args:
            stage: Usd Stage to inspect.

        """
        super().__init__()
        self._stage = stage

    def compose(self) -> ComposeResult:
        """Build the UI.

        Yields:
            ComposeResult.

        """
        yield Header()
        with HorizontalScroll():
            yield StageTree(self._stage, focus=True, classes="bordered_widget")
            yield PrimLayerStackTable(classes="bordered_widget")

        with HorizontalScroll(can_focus=False):
            # Tabs for the Prim Data.
            yield PrimDataTabs(id="prim_data_tabs", classes="bordered_widget")
            yield ValueDataTabs(id="value_data_tabs", classes="bordered_widget")
        yield Timeline(self._stage, id_selector="timeline")
        yield Footer()

    @on(StageTree.NodeHighlighted, "StageTree")
    def _stage_tree_node_highlighted(self, event: StageTree.NodeHighlighted) -> None:
        """Handle the selection of a prim node in the tree.

        Populate any widgets whose data depend on the currently selected prim.

        """
        # Update the widgets that depend on the selected prim.
        self.query_one(PrimLayerStackTable).prim = event.prim

    @on(PrimPropertiesTable.RowHighlighted, "PrimPropertiesTable")
    def _property_highlighted(
        self,
        event: PrimPropertiesTable.RowHighlighted,
    ) -> None:
        """Handle the selection of a prim property.

        Populate any widgets whose data depend on the currently selected property.

        """
        values_data_table = self.query_one(values_table.ValuesTable)
        # If the table is empty and the message is emitted the RowKey will be None
        if not event.row_key:
            values_data_table.state = values_table.NoValueDisplayState()
            return

        prim = self.query_one(PrimDataTabs).prim
        if not prim:
            values_data_table.state = values_table.NoValueDisplayState()
            return

        property_metadata_table = self.query_one(
            "#property_metadata_table",
            MetadataTable,
        )

        if isinstance(prim, Usd.Prim):
            prim_property = prim.GetProperty(str(event.row_key.value))
            values_data_table.state = values_table.PropertyValueDisplayState(
                prim_property,
            )
            property_metadata_table.data_object = prim_property

        if isinstance(prim, Sdf.PrimSpec):
            # A . must be appended at the beginning of the property name in
            # order for it to be a valid relative path.
            # https://openusd.org/dev/api/class_sdf_path.html#sec_SdfPath_Syntax
            prim_property = prim.GetPropertyAtPath(f".{event.row_key.value}")
            values_data_table.state = values_table.PropertySpecValueDisplayState(
                prim_property,
            )
            property_metadata_table.data_object = prim_property

    @on(MetadataTable.RowHighlighted, "#prim_metadata_table")
    def _prim_metadatum_highlighted(
        self,
        event: MetadataTable.RowHighlighted,
    ) -> None:
        values_data_table = self.query_one(values_table.ValuesTable)
        if not event.row_key:
            values_data_table.state = values_table.NoValueDisplayState()
            return

        metadata_value = event.data_table.get_cell(event.row_key, "value")
        values_data_table.state = values_table.MetadatumValueDisplayState(
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
            selected_prim_node = self.query_one(StageTree).cursor_node
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
        value_tabs = self.query_one("#value_data_tabs", ValueDataTabs)
        if str(event.tab.label) == "Properties":
            value_tabs.border_title = "Property Data"
            value_tabs.show_tab("metadata_tab")

        if str(event.tab.label) == "Metadata":
            value_tabs.hide_tab("metadata_tab")
            value_tabs.border_title = "Metadatum data"

    @on(Timeline.FrameChanged, "#timeline")
    def _frame_changed(self, event: Timeline.FrameChanged) -> None:
        """Handle frame changes by updating all time dependent widgets.

        Args:
            event: FrameChanged message posted by a Timeline.

        """
        if not event.frame:
            return

        frame = event.frame

        table = self.query_one("#values_table", values_table.ValuesTable)
        table.frame = frame
