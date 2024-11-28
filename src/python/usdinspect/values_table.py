"""Contains everything related to the Values table.

With the Values table I wanted to experiment and use the State pattern:
https://gameprogrammingpatterns.com/state.html

I liked the result quite a lot! The Values table is quite basic, the state classes are
the ones that encapsulate all the behavior to set up the table in a custom manner and
display a specific type of data.

"""

from abc import ABC, abstractmethod

from pxr import Sdf, Usd
from textual.reactive import reactive
from textual.widgets import DataTable


class DataTableDisplayState(ABC):
    """Abstract class for DataTable State objects."""

    def enter(self, table: DataTable) -> None:
        """Clear the table when a state is entered.

        Args:
            table: Table to clear.

        """
        table.clear()
        for key in list(table.columns):
            table.remove_column(key)

    @abstractmethod
    def apply(self, table: DataTable) -> None:
        """Abstract method for applying a state to the DataTable.

        Args:
            table: Table to apply the state to.

        """
        ...


class PropertyValueDisplayState(DataTableDisplayState):
    """Define the state of a DataTable to display the values of a Property."""

    def __init__(self, usd_property: Usd.Property | Sdf.PropertySpec) -> None:
        """Construct a PropertyValueDisplayState.

        Args:
            usd_property: Property or PropertySpec.

        """
        self.usd_property = usd_property
        super().__init__()

    def apply(self, table: DataTable) -> None:
        """Populate the table with value of an property."""
        if not self.usd_property:
            return
        table.clear()

        value = None
        is_array = False

        if isinstance(self.usd_property, Usd.Attribute):
            value = self.usd_property.Get()
            if value:
                # Check if the value of the attribute is an array.
                type_name = self.usd_property.GetTypeName()
                is_array = type_name.isArray

        if isinstance(self.usd_property, Usd.Relationship):
            value = self.usd_property.GetTargets()
            if value:
                # Relationships always return a list a list of paths.
                is_array = True

        if not value:
            table.add_column("No Value")
            return

        if is_array:
            table.add_columns("Index", "Value")
            for index, item in enumerate(value):
                table.add_row(index, item)
            return

        # If it's not an array then create a singe row that contains the value.
        table.add_column("Value")
        table.add_row(value)


class MetadatumValueDisplayState(DataTableDisplayState):
    """Define the state of a DataTable to display the values of a Metadatum."""

    def __init__(self, value: object) -> None:
        """Construct a MetadatumValueDisplayState.

        Args:
            value: The value that shoud be displayed in the UI.

        """
        self.value = value
        super().__init__()

    def apply(self, table: DataTable) -> None:
        """Apply the state to the DataTable.

        When this state is applied the table will have a single column `Value` and a
        single row that holds the value.

        Args:
            table: table to apply the state to.

        """
        table.add_columns("Value")
        table.add_row(self.value)


class NoValueDisplayState(DataTableDisplayState):
    """Define the state of a DataTable used when there isn't a value to be displayed."""

    def apply(self, table: DataTable) -> None:
        """Apply the state to the DataTable.

        When this state is applied the table will have a single column `Value` and a
        single row that holds the value.

        Args:
            table: table to apply the state to.

        """
        table.add_column("No Value")
        table.cursor_type = "row"


class ValuesTable(DataTable):
    """Widget that displays the values of a property in a table view."""

    state: reactive[DataTableDisplayState] = reactive(NoValueDisplayState())

    def watch_state(self) -> None:
        """Handle changes to the state of the table."""
        self.state.enter(self)
        self.state.apply(self)
