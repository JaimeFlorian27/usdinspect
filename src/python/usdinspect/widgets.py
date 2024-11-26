"""Module that contains multiple widgets used in this application."""

from typing import TYPE_CHECKING

from pxr import Sdf, Usd
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, ListItem, Tree

from . import usd_utils

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode


class StageTree(Tree):
    """Tree widget that presents a USD Stage."""

    BORDER_TITLE = "Stage Tree"
    stage: reactive[Usd.Stage | None] = reactive(None)

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


class PrimLayerListItem(ListItem):
    """..."""

    def __init__(
        self,
        *children: Widget,
        prim_spec: Sdf.PrimSpec | None = None,
    ) -> None:
        """..."""
        super().__init__(*children)
        self.prim_spec = prim_spec


class MetadataTable(DataTable):
    """Table that represents the metadata of a Usd Prim, Property and their specs."""

    usd_object: reactive[Usd.Object | None] = reactive(None, always_update=True)
    sdf_spec_object: reactive[Sdf.Spec | None] = reactive(None, always_update=True)

    def compose(self) -> ComposeResult:
        """Override compose to add cursor type and default columns.

        Returns:
            ComposeResult.

        """
        self.cursor_type = "row"
        self.add_columns("Field Name", "Value")
        return super().compose()

    def watch_usd_object(self) -> None:
        """Populate table with the metadata of a Usd Object."""
        if not self.usd_object:
            return

        self.clear()

        for field, value in usd_utils.get_object_metadata(self.usd_object):
            self.add_row(field, value)

    def watch_sdf_spec_object(self) -> None:
        """Populate table with the metadata of a Sdf Spec."""
        if not self.sdf_spec_object:
            return

        self.clear()

        for key, value in usd_utils.get_spec_metadata(self.sdf_spec_object):
            self.add_row(key, value)


class PrimLayerStackTable(DataTable):
    """DataTable that presents the layer stack of a USD Prim."""

    BORDER_TITLE = "Prim Layer Stack"
    prim: reactive[Usd.Prim | None] = reactive(None)

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

            self.add_row(
                layer.GetDisplayName(),
                composition_arc_name,
                key=f"{layer.identifier}|{spec.path}",
            )
        self.index = 0


class PrimPropertiesTable(DataTable):
    """Widget that displays the properties of a UsdPrim in a table view."""

    BORDER_TITLE = "Prim Properties"
    prim: reactive[Usd.Prim | Sdf.PrimSpec | None] = reactive(None, always_update=True)

    def compose(self) -> ComposeResult:
        """Compose the widget.

        Returns:
            ComposeResult of the widget.

        """
        self.cursor_type = "row"
        self.add_columns("Type", "Property", "Value Type")
        return super().compose()

    def watch_prim(self) -> None:
        """Populate the table with the properties of the current Prim."""
        if not self.prim:
            return

        self.clear()
        # item name as prop, property would shadow the python built-in.
        if isinstance(self.prim, Usd.Prim):
            for prop in self.prim.GetProperties():
                if isinstance(prop, Usd.Attribute):
                    self.add_row(
                        "Attr",
                        prop.GetName(),
                        prop.GetTypeName(),
                        key=prop.GetName(),
                    )
                if isinstance(prop, Usd.Relationship):
                    self.add_row(
                        "Rel",
                        prop.GetName(),
                        "",
                        key=prop.GetName(),
                    )
        if isinstance(self.prim, Sdf.PrimSpec):
            self.clear()
            for prop_spec in self.prim.properties:
                if isinstance(prop_spec, Sdf.AttributeSpec):
                    self.add_row(
                        "Attr",
                        prop_spec.name,
                        prop_spec.typeName,
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


class PropertyValuesTable(DataTable):
    """Widget that displays the values of a property in a table view."""

    BORDER_TITLE = "Values"

    property: reactive[Usd.Property | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Compose the widget.

        Returns:
            ComposeResult of the widget.

        """
        self.add_columns("Index", "Value")
        self.cursor_type = "row"
        return super().compose()

    def watch_property(self) -> None:
        """Populate the table with value of an property."""
        if not self.property:
            return
        self.clear()

        value = None
        is_array = False

        if isinstance(self.property, Usd.Attribute):
            value = self.property.Get()
            if not value:
                return

            # Check if the value of the attribute is an array.
            type_name = self.property.GetTypeName()
            is_array = type_name.isArray

        if isinstance(self.property, Usd.Relationship):
            value = self.property.GetTargets()
            if not value:
                return

            # Relationships always return a list a list of paths.
            is_array = True

        if not value:
            return

        if is_array:
            for index, item in enumerate(value):
                self.add_row(index, item)
            return

        # If it's not an array then create a singe row that contains the value.
        self.add_row("", value)
