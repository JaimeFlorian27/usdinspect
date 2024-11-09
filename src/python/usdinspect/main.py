"""Test file."""

from pathlib import Path
from typing import TYPE_CHECKING

from pxr.Usd import Prim, Stage
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Placeholder, Tree, DirectoryTree

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
        self._prim_properties_table = DataTable()

    def compose(self) -> ComposeResult:
        """Build the UI.

        Yields:
            ComposeResult.

        """
        yield Header()
        self._stage_tree.populate(self._stage)
        yield self._stage_tree

        self._prim_properties_table.add_columns("Type", "Property Name", "Value")
        yield self._prim_properties_table
        yield Footer()


if __name__ == "__main__":
    stage = Stage.Open("/home/jaime/Downloads/Kitchen_set/Kitchen_set.usd")
    app = UsdInspectApp(stage)
    app.run()
