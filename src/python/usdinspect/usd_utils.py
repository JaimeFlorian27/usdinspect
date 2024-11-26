"""Utilites for interacting with Usd data."""

from collections.abc import Iterator
from typing import Any

from pxr import Sdf, Usd


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
