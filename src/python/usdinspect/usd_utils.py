"""Utilites for interacting with Usd data."""

import dataclasses
from collections.abc import Iterator
from enum import Enum
from typing import Any

import colorhash
from pxr import Sdf, Usd
from rich.text import Text


class PropertyValueColors(Enum):
    """Colors to use to represent the type of values for a property or its specs."""

    NONE = ""
    NO_VALUE = "#5c5c5c"
    FALLBACK = "#d6990b"
    DEFAULT = "#9ad4f5"
    CUSTOM = "#f59a9a"
    TIME_SAMPLES = "#99db81"
    VALUE_CLIPS = "#db81db"


@dataclasses.dataclass
class RowData:
    """Representation of a Usd Object for display in a DataTable Row."""

    name: Text
    label: Text
    value: Text
    value_type: Text

    @classmethod
    def from_property(cls, prop: Usd.Property) -> "RowData":
        """Initialize a RowData object from a Usd Property.

        Args:
            prop: Usd Property.

        Returns:
            RowData object that represents the property.

        """
        label_style: PropertyValueColors = PropertyValueColors.NONE
        value_type = ""
        if isinstance(prop, Usd.Attribute):
            if not prop.HasValue():
                label_style = PropertyValueColors.NO_VALUE

            elif prop.HasFallbackValue() and not prop.HasAuthoredValue():
                label_style = PropertyValueColors.FALLBACK

            # The attribute has an authored value.
            else:
                label_style = PropertyValueColors.DEFAULT

                if prop.ValueMightBeTimeVarying():
                    label_style = PropertyValueColors.TIME_SAMPLES

            value_type = str(prop.GetTypeName())

        label = Text("Attr", style=label_style.value)
        # The color of the name will be the color hash of the strongest layer.
        name_style: str = ""
        if prop.GetPropertyStack():
            name_style = colorhash.ColorHash(
                prop.GetPropertyStack()[0].layer,
            ).hex

        name = Text(prop.GetName(), name_style)

        return RowData(name, label, Text(), Text(value_type))

    @classmethod
    def from_property_spec(cls, prop_spec: Sdf.PropertySpec) -> "RowData":
        """Initialize a RowData object from a Usd PropertySpec.

        Args:
            prop_spec: Usd Property Spec.

        Returns:
            RowData object that represents the property.

        """
        label_style: PropertyValueColors = PropertyValueColors.NONE
        value_type = ""
        if isinstance(prop_spec, Sdf.AttributeSpec):
            if not prop_spec.HasDefaultValue():
                label_style = PropertyValueColors.NO_VALUE

            else:
                label_style = PropertyValueColors.DEFAULT
            value_type = str(prop_spec.typeName)

        label = Text("Attr", style=label_style.value)
        # The color of the name will be the color hash of the  spec's layer.
        name_style = colorhash.ColorHash(prop_spec.layer).hex or ""

        name = Text(prop_spec.name, name_style)

        return RowData(name, label, Text(), Text(value_type))


def get_object_metadata(usd_object: Usd.Object) -> Iterator[tuple[str, Any]]:
    """Iterate over the Metadata, AssetInfo and CustomData of a Usd Object.

    Yields:
        Key-value item pairs for each metadatum.

    """
    metadata_dicts: list[dict[str, Any]] = [
        usd_object.GetAllMetadata(),
        usd_object.GetAssetInfo(),
        usd_object.GetCustomData(),
    ]
    for metadata_dict in metadata_dicts:
        yield from metadata_dict.items()


def get_spec_metadata(spec: Sdf.Spec) -> Iterator[tuple[str, Any]]:
    """Iterate over the Metadata of a Sdf Spec.

    Only PrimSpec and PropertySpec obejcts have AssetInfo and CustomData.

    Yields:
        Key-value item pairs for each metadatum.

    """
    for key in spec.ListInfoKeys():
        yield (key, spec.GetInfo(key))

    if isinstance(spec, Sdf.PrimSpec | Sdf.PropertySpec):
        yield from spec.assetInfo.items()
        yield from spec.customData.items()
