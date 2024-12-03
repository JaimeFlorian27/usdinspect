"""Contains everything related to the Values table.

With the Values table I wanted to experiment and use the State pattern:
https://gameprogrammingpatterns.com/state.html

I liked the result quite a lot! The Values table is quite basic, the state classes are
the ones that encapsulate all the behavior to set up the table in a custom manner and
display a specific type of data.

"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pxr import Sdf, Usd
from textual.reactive import reactive
from textual.widgets import DataTable


class ValuesTableDisplayState(ABC):
    """Abstract class for ValuesTable State objects."""

    frame_dependent = False

    def enter(self, table: ValuesTable) -> None:
        """Clear the table when a state is entered.

        Args:
            table: Table to clear.

        """
        table.clear()
        for key in list(table.columns):
            table.remove_column(key)

    @abstractmethod
    def apply(self, table: ValuesTable) -> None:
        """Abstract method for applying a state to the ValuesTable.

        Args:
            table: Table to apply the state to.

        """
        ...


class PropertyValueDisplayState(ValuesTableDisplayState):
    """Define the state of a ValuesTable to display the values of a Property."""

    frame_dependent = True

    def __init__(self, usd_property: Usd.Property) -> None:
        """Construct a PropertyValueDisplayState.

        Args:
            usd_property: Property or PropertySpec.
            frame: Frame at which the property should be evaluated.

        """
        self.usd_property = usd_property
        super().__init__()

    def apply(self, table: ValuesTable) -> None:
        """Populate the table with value of an property."""
        if not self.usd_property:
            return
        table.clear()

        value = None
        is_array = False

        if isinstance(self.usd_property, Usd.Attribute):
            value = self.usd_property.Get(table.frame)
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


class PropertySpecValueDisplayState(ValuesTableDisplayState):
    """Define the state of a ValuesTable to display the values of a Property Spec."""

    def __init__(self, usd_property: Sdf.PropertySpec) -> None:
        """Construct a PropertyValueDisplayState.

        Args:
            usd_property: Property or PropertySpec.

        """
        self.prop_spec = usd_property
        super().__init__()

    def apply(self, table: ValuesTable) -> None:
        """Populate the table with value of an property."""
        if not self.prop_spec:
            return
        table.clear()

        value = None
        is_array = False

        if isinstance(self.prop_spec, Sdf.AttributeSpec):
            layer = self.prop_spec.layer
            value = None
            # REVISIT: When moving back to 24.11 the TimeSamples methods will have
            # moved from the layer to the AttributeSpec.
            time_sample_count = layer.GetNumTimeSamplesForPath(self.prop_spec.path)

            if time_sample_count:
                value = []
                is_array = True

                # Populate the value array with the values of the time samples for the
                # attribute.
                for time_sample in layer.ListTimeSamplesForPath(self.prop_spec.path):
                    value.append(
                        layer.QueryTimeSample(self.prop_spec.path, time_sample),
                    )

            else:
                value = self.prop_spec.default
                if value:
                    # Check if the value of the attribute is an array.
                    type_name = self.prop_spec.typeName
                    is_array = type_name.isArray

        if isinstance(self.prop_spec, Sdf.RelationshipSpec):
            value = self.prop_spec.targetPathList.explicitItems
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


class MetadatumValueDisplayState(ValuesTableDisplayState):
    """Define the state of a ValuesTable to display the values of a Metadatum."""

    frame_dependent = False

    def __init__(self, value: object) -> None:
        """Construct a MetadatumValueDisplayState.

        Args:
            value: The value that shoud be displayed in the UI.

        """
        self.value = value
        super().__init__()

    def apply(self, table: ValuesTable) -> None:
        """Apply the state to the ValuesTable.

        When this state is applied the table will have a single column `Value` and a
        single row that holds the value.

        Args:
            table: table to apply the state to.

        """
        table.add_columns("Value")
        table.add_row(self.value)


class NoValueDisplayState(ValuesTableDisplayState):
    """Define the state of a ValuesTable when there isn't a value to be displayed."""

    def apply(self, table: ValuesTable) -> None:
        """Apply the state to the ValuesTable.

        When this state is applied the table will have a single column `Value` and a
        single row that holds the value.

        Args:
            table: table to apply the state to.

        """
        table.add_column("No Value")
        table.cursor_type = "row"


class ValuesTable(DataTable):
    """Widget that displays the values of a property in a table view."""

    state: reactive[ValuesTableDisplayState] = reactive(NoValueDisplayState())
    frame: reactive[int] = reactive(0)

    def watch_state(self) -> None:
        """Handle changes to the state of the table."""
        self.state.enter(self)
        self.state.apply(self)

    def watch_frame(self) -> None:
        """When the frame changes re-apply the current state if it's frame_dependent."""
        if self.state.frame_dependent:
            self.state.enter(self)
            self.state.apply(self)
