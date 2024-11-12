"""Module that contains multiple widgets used in this application."""

from typing import TYPE_CHECKING

from pxr.Usd import Prim, Stage
from textual.widgets import Tree

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode


class StageTree(Tree):
    """Tree widget that presents a USD Stage."""

    def populate(self, stage: Stage) -> None:
        """Populate the tree hierarchy with prims.

        This method iterates throug a stage using its Traverse method.

        Args:
        stage: USD Stage.

        """
        self.root.expand()

        prim_to_node: dict[Prim, TreeNode] = {}
        root_prim = stage.GetPseudoRoot()

        # This dict will store a mapping between the prims and their respective node
        # in the tree, this is useful for constructing the hierarchy while traversing
        # the stage.
        prim_to_node[root_prim] = self.root

        for prim in stage.Traverse():
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
