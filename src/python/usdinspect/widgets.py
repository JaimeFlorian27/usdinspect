"""Module that contains multiple widgets used in this application."""

from __future__ import annotations

from typing import TYPE_CHECKING

import colorhash
from pxr import Sdf, Usd
from rich.text import Text
from textual import on
from textual.containers import (
    HorizontalGroup,
    VerticalGroup,
)
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)
from textual_slider import Slider

from usdinspect import values_table

from . import usd_utils

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.widgets.data_table import RowKey
    from textual.widgets.tree import EventTreeDataType, TreeNode


class StageTree(Tree):
    """Tree widget that presents a USD Stage."""

    class NodeHighlighted(Tree.NodeHighlighted):
        """Overrides thhe NodeHighlighted message to pass a prim."""

        def __init__(self, node: TreeNode[EventTreeDataType]) -> None:
            """Initialize the class."""
            super().__init__(node)

            tree = node.tree
            prim_path = str(node.data)
            if not prim_path:
                return

            self.prim = None
            if isinstance(tree, StageTree):
                if not tree.stage:
                    return
                self.prim = tree.stage.GetPrimAtPath(prim_path)
                tree.prim = self.prim

    BORDER_TITLE = "Stage Tree"
    stage: reactive[Usd.Stage | None] = reactive(None)

    def __init__(
        self,
        stage: Usd.Stage,
        name: str | None = None,
        id_selector: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        focus: bool = True,
    ) -> None:
        """Initialize a StageTree.

        Args:
            stage: Usd Stage that the tree will represent.
            name: Name of the widget.
            id_selector: Id for the widgets.
            classes: CSS classes for the widget.
            disabled: If the widget should be disabled.
            focus: If the widget should be focused.

        """
        super().__init__(
            "/",
            "/",
            name=name,
            id=id_selector,
            classes=classes,
            disabled=disabled,
        )
        if focus:
            self.focus()
        self.prim: Usd.Prim | None = None
        self.stage = stage

    def watch_stage(self) -> None:
        """Populate the tree hierarchy with prims.

        This method iterates through a stage using its Traverse method.

        Args:
        stage: USD Stage.

        """
        if not self.stage:
            return

        self.root.expand()

        prim_to_node: dict[Usd.Prim, TreeNode] = {}
        root_prim = self.stage.GetPseudoRoot()

        # This dict will store a mapping between the prims and their respective node
        # in the tree, this is useful for constructing the hierarchy while traversing
        # the stage.
        prim_to_node[root_prim] = self.root

        for prim in self.stage.Traverse():
            if prim == root_prim:
                continue

            parent_prim = prim.GetParent()
            if not parent_prim:
                continue

            parent_node = prim_to_node.get(parent_prim)
            if not parent_node:
                continue

            # Add regular nodes or leafs based on the number of children the prim has.
            if prim.GetAllChildren():
                current_node = parent_node.add(prim.GetName(), prim.GetPath())
                prim_to_node[prim] = current_node
            else:
                current_node = parent_node.add_leaf(prim.GetName(), prim.GetPath())


class MetadataTable(DataTable):
    """Table that represents the metadata of a Usd Prim, Property and their specs."""

    data_object: reactive[Usd.Object | Sdf.Spec | None] = reactive(None)

    def on_mount(self) -> None:
        """Construct the table after is has been mounted."""
        self.cursor_type = "row"
        self.add_column("Field Name", key="name")
        self.add_column("Type", key="type")
        self.add_column("Value", key="value")
        return super().on_mount()

    def watch_data_object(self) -> None:
        """Populate table with the metadata of a Usd Object."""
        if not self.data_object:
            return

        self.clear()

        data = None
        if isinstance(self.data_object, Sdf.Spec):
            data = usd_utils.get_spec_metadata(self.data_object)
        elif isinstance(self.data_object, Usd.Object):
            data = usd_utils.get_object_metadata(self.data_object)

        if not data:
            return

        for metadatum, value in data:
            self.add_row(metadatum, type(value).__name__, value, key=metadatum)


class PrimLayerStackTable(DataTable):
    """DataTable that presents the layer stack of a USD Prim."""

    BORDER_TITLE = "Prim Layer Stack"
    prim: reactive[Usd.Prim | None] = reactive(None)
    current_spec: Sdf.PrimSpec | None = None

    class LayerChanged(Message):
        """Message posted when the selected layer changes."""

        def __init__(
            self,
            data_table: PrimLayerStackTable,
            cursor_row: int,
            row_key: RowKey,
        ) -> None:
            """Construct a LayerChanged Message.

            Args:
                data_table: Table that emitted the message.
                cursor_row: Row that is currently highlighted.
                row_key: Key of the highlighted row.

            """
            super().__init__()
            self.cursor_row = cursor_row
            self.row_key = row_key
            self.data_table = data_table
            self.current_spec = data_table.current_spec

        @property
        def control(self) -> PrimLayerStackTable:
            """Control that posted this message.

            Returns:
                PrimLayerStackTable instance.

            """
            return self.data_table

    def compose(self) -> ComposeResult:
        """Override compose to add cursor type and default columns.

        Returns:
            ComposeResult.

        """
        self.cursor_type = "row"
        self.add_columns("Layer", "Composition Arc")
        return super().compose()

    def watch_prim(self) -> None:
        """Populate table with all the layers that have a spec on the prim.

        Args:
        prim: USD Prim.

        """
        if not self.prim:
            return

        self.clear()
        self.add_row("Composed", "", key="composed")

        composition_arcs: list[Usd.CompositionArc] = Usd.PrimCompositionQuery(
            self.prim,
        ).GetCompositionArcs()

        prim_stack = self.prim.GetPrimStack()

        """
        Use the two-pointer method to match layers in the prim stack with the
        composition arc that is introducing them. Both lists are ordered from
        strongest to weakest opinion which allows this method to work.

        I need to do it this way as the composition query does not show all the
        layers that affect a prim, it doesn't retrieve sublayers specifically, this is
        because sublayers are not a composition arc that target prims such as payloads
        or inherits, sublayers target a stage or layer.

        We should be able to safely assume that a layer that:
        - Has a spec in the prim.
        - Is not present in the composition arcs list.
        Is a sublayer.
        """
        current_arc_index = 0
        for spec in prim_stack:
            layer = spec.layer
            composition_arc_name = "Sublayer"

            if current_arc_index < len(composition_arcs):
                current_arc = composition_arcs[current_arc_index]
                if layer == current_arc.GetTargetLayer():
                    composition_arc_name = current_arc.GetArcType().displayName
                    current_arc_index += 1

            row_color = colorhash.ColorHash(layer).hex
            self.add_row(
                Text(layer.GetDisplayName(), style=row_color),
                composition_arc_name,
                key=f"{layer.identifier}|{spec.path}",
            )
        self.index = 0

    @on(DataTable.RowHighlighted, "PrimLayerStackTable")
    def _handle_row_highlighted(
        self, event: PrimLayerStackTable.RowHighlighted,
    ) -> None:
        """Handle row highlighting in the PrimLayerStackTable.

        Args:
            event: RowHighlighted message posted by the PrimLayerStackTable.

        """
        row_key: str | None = event.row_key.value
        if not row_key:
            return

        if event.row_key.value != "composed":
            layer_path, prim_spec_path = row_key.split("|")
            self.current_spec = Sdf.Layer.FindOrOpen(layer_path).GetPrimAtPath(
                prim_spec_path,
            )
        else:
            self.current_spec = None

        self.post_message(self.LayerChanged(self, event.cursor_row, event.row_key))


class PrimPropertiesTable(DataTable):
    """Widget that displays the properties of a UsdPrim in a table view."""

    BORDER_TITLE = "Prim Properties"
    data_object: reactive[Usd.Prim | Sdf.PrimSpec | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Compose the widget.

        Returns:
            ComposeResult of the widget.

        """
        self.cursor_type = "row"
        self.add_columns("Type", "Property", "Value Type")
        return super().compose()

    def watch_data_object(self) -> None:
        """Populate the table with the properties of the current Prim."""
        if not self.data_object:
            return

        self.clear()
        # item name as prop, property would shadow the python built-in.
        if isinstance(self.data_object, Usd.Prim):
            for prop in self.data_object.GetProperties():
                if isinstance(prop, Usd.Attribute):
                    row_data = usd_utils.RowData.from_property(prop)
                    self.add_row(
                        row_data.label,
                        row_data.name,
                        row_data.value_type,
                        key=prop.GetName(),
                    )
                if isinstance(prop, Usd.Relationship):
                    self.add_row(
                        "Rel",
                        prop.GetName(),
                        "",
                        key=prop.GetName(),
                    )

        if isinstance(self.data_object, Sdf.PrimSpec):
            self.clear()
            for prop_spec in self.data_object.properties:
                if isinstance(prop_spec, Sdf.AttributeSpec):
                    row_data = usd_utils.RowData.from_property_spec(prop_spec)
                    self.add_row(
                        row_data.label,
                        row_data.name,
                        row_data.value_type,
                        key=prop_spec.name,
                    )
                if isinstance(prop_spec, Sdf.RelationshipSpec):
                    self.add_row(
                        "Rel",
                        prop_spec.name,
                        "",
                        key=prop_spec.name,
                    )
        return


class PrimDataTabs(TabbedContent):
    """TabbedContent that holds widgets that represents data of a Prim."""

    BORDER_TITLE = "Prim Data"
    prim: reactive[Usd.Prim | Sdf.PrimSpec | None] = reactive(None)

    def on_mount(self) -> None:
        """Set up the PrimDataTabs.

        This method adds the TabPanes that display the Prim Data.
        """
        self.add_pane(
            TabPane(
                "Properties",
                PrimPropertiesTable(
                    id="prim_properties_table",
                    classes="prim_data_holder",
                ),
                id="prim_properties_tab",
            ),
        )
        self.add_pane(
            TabPane(
                "Metadata",
                MetadataTable(id="prim_metadata_table", classes="prim_data_holder"),
                id="prim_metadata_table",
            ),
        )

    def watch_prim(self) -> None:
        """React to changes of the Prim attribute."""
        if not self.prim:
            return

        if not self.active_pane:
            return

        active_widget = self.active_pane.query_one(
            ".prim_data_holder",
        )

        if isinstance(active_widget, PrimPropertiesTable | MetadataTable):
            active_widget.data_object = self.prim

    @on(TabbedContent.TabActivated, "PrimDataTabs")
    def _prim_data_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """Handle changing tabs.

        this method is in charge of making sure that the prim_data_holder widget that
        becomes visible when a tab is changed has its data_object updated.

        Args:
            event: Event that triggered a call to this method.

        """
        if not event.tabbed_content:
            return
        active_pane = event.tabbed_content.active_pane

        if not active_pane:
            return
        active_widget = active_pane.query_one(
            ".prim_data_holder",
        )

        if isinstance(active_widget, PrimPropertiesTable | MetadataTable):
            active_widget.data_object = self.prim


class ValueDataTabs(TabbedContent):
    """TabbedContent that holds widgets that represents data of a property, metadata."""

    BORDER_TITLE = "Property Data"
    prim: reactive[Usd.Prim | Sdf.PrimSpec | None] = reactive(None)

    def on_mount(self) -> None:
        """Set up the PrimDataTabs.

        This method adds the TabPanes that display the Prim Data.
        """
        self.add_pane(
            TabPane(
                "Values",
                values_table.ValuesTable(id="values_table"),
                id="value_tab",
            ),
        )
        self.add_pane(
            TabPane(
                "Metadata",
                MetadataTable(id="property_metadata_table"),
                id="metadata_tab",
            ),
        )


class PrimLayerTabs(TabbedContent):
    """TabbedContent widget that contains a PrimLayerStackTable and a MetadataTable."""

    BORDER_TITLE = "Prim Layer Data"

    prim: reactive[Usd.Prim | None] = reactive(None)
    selected_layer: Sdf.Layer | None = None

    def on_mount(self) -> None:
        """Add the TabPanes that compose the widget."""
        self.add_pane(
            TabPane(
                "Layer Stack",
                PrimLayerStackTable(
                    id="prim_layer_stack_table",
                    classes="layer_data_holder",
                ),
                id="prim_layer_stack_tab",
            ),
        )
        self.add_pane(
            TabPane(
                "Layer Metadata",
                MetadataTable(id="layer_metadata_table", classes="layer_data_holder"),
                id="layer_metadata_tab",
            ),
        )

    def watch_prim(self) -> None:
        """React to changes of the Prim attribute."""
        if not self.prim:
            return

        if not self.active_pane:
            return

        active_widget = self.active_pane.query_one(
            ".layer_data_holder",
        )

        if isinstance(active_widget, PrimLayerStackTable):
            active_widget.prim = self.prim

    @on(TabbedContent.TabActivated, "PrimLayerTabs")
    def _prim_layer_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """Handle changing tabs.

        this method is in charge of making sure that the layer_data_holder widget that
        becomes visible when the tab is changed has its data_object updated.

        Args:
            event: Event that triggered a call to this method.

        """
        if not event.tabbed_content:
            return
        active_pane = event.tabbed_content.active_pane

        if not active_pane:
            return

        active_widget = active_pane.query_one(
            ".layer_data_holder",
        )

        if isinstance(active_widget, MetadataTable):
            pseudo_root: Sdf.PrimSpec | None = None
            if self.selected_layer:
                pseudo_root = self.selected_layer.pseudoRoot

            active_widget.data_object = pseudo_root

    @on(PrimLayerStackTable.LayerChanged, "#prim_layer_stack_table")
    def _selected_layer_changed(self, event: PrimLayerStackTable.LayerChanged) -> None:
        if not event.current_spec:
            self.selected_layer = None
            self.hide_tab("layer_metadata_tab")
            return

        self.selected_layer = event.current_spec.layer
        self.show_tab("layer_metadata_tab")


class Timeline(Static):
    """Widget that allows displays and controls the current frame.

    Currently composed by a slider and a label that shows the current frame.

    The min and max values of the slider are determined from the Start and End TimeCode
    of the USD Stage.
    """

    class FrameChanged(Message):
        """Message posted when the frame changes in the timeline."""

        def __init__(self, timeline: Timeline, frame: int) -> None:
            """Notify that the frame changed in the timeline widget.

            Args:
                timeline: Timeline that sends the message.
                frame: Frame that the timeline was changed to.

            """
            self.frame = frame
            self.timeline = timeline
            super().__init__()

        @property
        def control(self) -> Timeline:
            """Control that posted this message.

            Returns:
                Timeline instance.

            """
            return self.timeline

    def __init__(
        self,
        stage: Usd.Stage,
        name: str | None = None,
        id_selector: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize a Timeline instance.

        Args:
            stage: USD Stage.
            name: Name of the widget.
            id_selector: ID of the widget, serves as CSS selector.
            classes: Classes of the widget, serves as CSS selectors.
            disabled: If the widget should be disabled by default.

        """
        self.stage = stage
        self.current_frame = 0
        super().__init__(
            name=name,
            id=id_selector,
            classes=classes,
            disabled=disabled,
        )

    def compose(self) -> ComposeResult:
        """Populate the timeline Widget.

        Yields:
            Widgets wrapped as a ComposeResult.

        """
        start_frame: int = int(self.stage.GetStartTimeCode() or 1)
        end_frame: int = int(self.stage.GetEndTimeCode() or 100)
        with VerticalGroup():
            yield Label("Frame:", id="frame_label")
            with HorizontalGroup():
                yield Input(
                    str(start_frame),
                    id="start_frame_input",
                    classes="timeline_input",
                    type="integer",
                )
                yield Slider(
                    min=start_frame,
                    max=end_frame,
                    id="framerange_slider",
                )
                yield Input(
                    str(end_frame),
                    id="end_frame_input",
                    classes="timeline_input",
                    type="integer",
                )

    @on(Slider.Changed, "#framerange_slider")
    def _frame_changed(self, event: Slider.Changed) -> None:
        """Handle frame changes.

        Args:
            event: Changed message posted by the Slider widget.

        """
        if not event.value:
            return

        frame = int(event.value)
        self.current_frame = frame

        frame_label = self.query_one("#frame_label", Label)
        frame_label.update(f"Frame: {frame}")
        self.post_message(self.FrameChanged(self, frame))

    @on(Input.Changed, "#start_frame_input")
    def _start_frame_changed(self, event: Input.Changed) -> None:
        """Handle value changes in the start frame input.

        Args:
            event: Changed message posted by the Input widget.

        """
        if not event.value.isdigit():
            return

        start_frame = int(event.value)
        slider = self.query_one("#framerange_slider", Slider)

        if not start_frame < slider.max:
            return
        slider.min = start_frame
        slider.value = max(start_frame, slider.value)

    @on(Input.Changed, "#end_frame_input")
    def _end_frame_changed(self, event: Input.Changed) -> None:
        """Handle value changes in the end frame input.

        Args:
            event: Changed message posted by the Input widget.

        """
        if not event.value.isdigit():
            return

        end_frame = int(event.value)
        slider = self.query_one("#framerange_slider", Slider)

        if not end_frame > slider.min:
            return

        slider.max = end_frame
        slider.value = min(end_frame, slider.value)
