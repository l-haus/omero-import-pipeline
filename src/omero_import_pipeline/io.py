import os
from typing import Dict, List, Union

import numpy as np
import tifffile
from ome_types import OME, to_xml
from ome_types.model import (
    Channel,
    Image,
    LightPath,
    Pixels,
    Pixels_DimensionOrder,
    PixelType,
    Plane,
)

from omero_import_pipeline.datatypes import ImageGroup, OMEImageMetadata
from omero_import_pipeline.metadata import extract_ome_metadata


def write_ome_tiff(
    file_name: str,
    img_stack: np.ndarray,  # shape: (C, H, W)
    output_dir: Union[str, os.PathLike],
    metadata: OMEImageMetadata,
    is_normalized: bool = False,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, file_name)

    c, h, w = img_stack.shape

    # Compose OME metadata
    channels = [
        Channel(
            id=f"Channel:{i}",
            name=metadata.channel_name or f"Channel {i}",
            samples_per_pixel=1,
            light_path=LightPath(),
        )
        for i in range(c)
    ]

    planes = [
        Plane(
            the_c=i,
            the_z=0,
            the_t=0,
            exposure_time=metadata.exposure_time if metadata.exposure_time else None,
        )
        for i in range(c)
    ]

    pixels = Pixels(
        id="Pixels:0",
        size_c=c,
        size_z=1,
        size_t=1,
        size_x=w,
        size_y=h,
        type=PixelType(img_stack.dtype.name),
        channels=channels,
        planes=planes,
        dimension_order=Pixels_DimensionOrder("XYZCT"),
        big_endian=False,
    )

    image = Image(
        id="Image:0",
        name=f"{metadata.well}_{metadata.channel_name}"
        if metadata.well and metadata.channel_name
        else "OME Image",
        description="16-bit to 8-bit using linear scaling" if is_normalized else None,
        pixels=pixels,
    )

    ome = OME(images=[image])
    description = to_xml(ome)

    # Write TIFF with embedded OME-XML
    tifffile.imwrite(
        out_path,
        data=img_stack.astype(img_stack.dtype),
        dtype=img_stack.dtype,
        photometric="minisblack",
        metadata=None,  # must be None when using description
        description=description,
        imagej=False,
    )


def read_tiff_group(paths: List[str]) -> ImageGroup:
    """
    Reads the first page of each TIFF file and stacks into a
    NumPy array of shape (C, H, W).

    Parameters:
        paths: List of file paths, one per channel, ordered.

    Returns:
        np.ndarray: Image stack of shape (channels, height, width)
    """
    images = []
    metadata = []

    for path in paths:
        with tifffile.TiffFile(path) as tif:
            images.append(tif.pages[0].asarray())
        metadata.append(extract_ome_metadata(path))

    return ImageGroup(np.stack(images, axis=0), metadata)


def get_ordered_channel_names(channel_dict: Dict[str, str]) -> List[str]:
    """
    Returns channel names in insertion order from a channel dictionary.

    Parameters:
        channel_dict: Dict mapping channel name to image path.

    Returns:
        List of channel names.
    """
    return list(channel_dict.keys())


def get_ordered_paths(channel_dict: Dict[str, str]) -> List[str]:
    """
    Returns a list of file paths ordered by channel name insertion order.

    Parameters:
        channel_dict: Dict mapping channel name to image path.

    Returns:
        List of file paths in order.
    """
    return [channel_dict[ch] for ch in get_ordered_channel_names(channel_dict)]


def read_merged_image(path: str) -> np.ndarray:
    """
    Reads a merged RGB image from a TIFF file and returns it as (3, H, W).

    Parameters:
        path: Path to the merged image TIFF file.

    Returns:
        np.ndarray: 3-channel image in (C, H, W) format.
    """
    with tifffile.TiffFile(path) as tif:
        img = tif.pages[0].asarray()  # Expect shape (H, W, 3)

    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError(f"Expected RGB image with shape (H, W, 3), got {img.shape}")

    # Convert from (H, W, 3) to (3, H, W)
    return np.transpose(img, (2, 0, 1))
