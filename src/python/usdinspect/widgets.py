"""Module that contains multiple widgets used in this application."""

from typing import TYPE_CHECKING

from pxr.Sdf import AttributeSpec, PrimSpec
from pxr.Usd import Attribute, Prim, Stage
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, ListItem, Tree

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode


class StageTree(Tree):
    """Tree widget that presents a USD Stage."""

    BORDER_TITLE = "Stage Tree"
    stage: reactive[Stage | None] = reactive(None)

    def watch_stage(self) -> None:
        """Populate the tree hierarchy with prims.

        This method iterates through a stage using its Traverse method.

        Args:
        stage: USD Stage.

        """
        if not self.stage:
            return

        self.root.expand()

        prim_to_node: dict[Prim, TreeNode] = {}
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

    def __init__(self, *children: Widget, prim_spec: PrimSpec | None = None) -> None:
        """..."""
        super().__init__(*children)
        self.prim_spec = prim_spec


class PrimMetadataTable(DataTable):
    """DataTable that represents the metadata of a Usd Prim."""

    BORDER_TITLE = "Prim Layer Stack"
    prim: reactive[Prim | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Override compose to add cursor type and default columns.

        Returns:
            ComposeResult.

        """
        self.cursor_type = "row"
        self.add_columns("Field Name", "Value")
        return super().compose()

    def watch_prim(self) -> None:
        """Populate table with the metadata of a prim.

        Args:
        prim: USD Prim.

        """
        if not self.prim:
            return

        self.clear()
        for field, value in self.prim.GetAllMetadata().items():
            self.add_row(field, value)


class PrimLayerStackTable(DataTable):
    """DataTable that presents the layer stack of a USD Prim."""

    BORDER_TITLE = "Prim Layer Stack"
    prim: reactive[Prim | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Override compose to add cursor type and default columns.

        Returns:
            ComposeResult.

        """
        self.cursor_type = "row"
        self.add_columns("Layer", "Specifier")
        return super().compose()

    def watch_prim(self) -> None:
        """Populate table with all the layers that have a spec on the prim.

        Args:
        prim: USD Prim.

        """
        if not self.prim:
            return

        self.clear()
        prim_stack = self.prim.GetPrimStack()
        self.add_row("Composed", "", key="composed")
        for spec in prim_stack:
            self.add_row(
                spec.layer.GetDisplayName(),
                spec.specifier.displayName,
                key=f"{spec.layer.realPath}:{spec.path}",
            )
        # Always select the first item as it is the composed stage.
        self.index = 0


class PrimAttributesTable(DataTable):
    """Widget that displays the attributes of a UsdPrim in a table view."""

    prim: reactive[Prim | None] = reactive(None, always_update=True)
    prim_spec: reactive[PrimSpec | None] = reactive(None, always_update=True)

    def compose(self) -> ComposeResult:
        """Compose the widget.

        Returns:
            ComposeResult of the widget.

        """
        self.cursor_type = "row"
        self.add_columns("Type", "Attribute Name")
        return super().compose()

    def watch_prim(self) -> None:
        """Populate the table with the attributes of the current Prim."""
        if not self.prim:
            return

        self.clear()
        for attribute in self.prim.GetAttributes():
            self.add_row(
                attribute.GetTypeName(),
                attribute.GetName(),
                key=attribute.GetName(),
            )
        return

    def watch_prim_spec(self) -> None:
        """Populate the table with the attributes of the current PrimSpec."""
        if not self.prim_spec:
            return

        self.clear()
        for attribute in self.prim_spec.attributes:
            attribute: AttributeSpec
            self.add_row(
                attribute.typeName,
                attribute.name,
                key=attribute.name,
            )
        return


class AttributeValuesTable(DataTable):
    """Widget that displays the values of an attribute in a table view."""

    BORDER_TITLE = "Values"

    attribute: reactive[Attribute | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Compose the widget.

        Returns:
            ComposeResult of the widget.

        """
        self.add_columns("Index", "Value")
        self.cursor_type = "row"
        return super().compose()

    def watch_attribute(self) -> None:
        """Populate the table with value of an attribute."""
        if not self.attribute:
            return

        self.clear()

        value = self.attribute.Get()
        if not value:
            return

        # Check if the value of the attribute is an array.
        type_name = self.attribute.GetTypeName()

        if type_name.isArray:
            for index, item in enumerate(value):
                self.add_row(index, item)
            return

        self.add_row("", value)
