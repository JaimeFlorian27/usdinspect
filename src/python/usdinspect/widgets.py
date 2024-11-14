"""Module that contains multiple widgets used in this application."""

from typing import TYPE_CHECKING

from pxr.Usd import Attribute, Prim, Stage
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Label, ListItem, ListView, Tree

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


class PrimCompositionList(ListView):
    """Tree widget that presents the opinion composition of a USD Prim."""

    BORDER_TITLE = "Prim Layers List"
    prim: reactive[Prim | None] = reactive(None)

    def watch_prim(self) -> None:
        """Populate list with all the layers that have a spec on the prim.

        Args:
        prim: USD Prim.

        """
        if not self.prim:
            return

        self.clear()
        prim_stack = self.prim.GetPrimStack()
        self.append(ListItem(Label("Composed")))
        for spec in prim_stack:
            self.append(ListItem(Label(spec.layer.GetDisplayName())))


class PrimAttributesTable(DataTable):
    """Widget that displays the attributes of a UsdPrim in a table view."""

    prim: reactive[Prim | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Compose the widget.

        Returns:
            ComposeResult of the widget.

        """
        self.cursor_type = "row"
        self.add_columns("Type", "Attribute Name")
        return super().compose()

    def watch_prim(self) -> None:
        """Populate the table with the data for the passed UsdPrim."""
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
