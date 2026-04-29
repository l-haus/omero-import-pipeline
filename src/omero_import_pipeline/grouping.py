import os
from typing import Dict, List, Tuple

import numpy as np

from omero_import_pipeline.datatypes import FieldOfView

def build_fov_dict(path: str, named_files: bool = True) -> Dict[str, FieldOfView]:
    image_groups = group_image_paths(path)
    field_of_views = {}
    for i, img_grp in enumerate(image_groups):
        well, well_fov_id, channel_dict = create_channel_mapping(img_grp)

        fov = FieldOfView(
            well=well, well_fov_id=well_fov_id, channel_file_paths=channel_dict
        )
        key = f"{well}_{well_fov_id}" if named_files else f"field_{str(i)}"
        field_of_views[key] = fov
    return field_of_views


def group_image_paths(path: str, mode: str = "R") -> List[List[str]]:
    """
    Groups TIFF image paths by field of view.

    Parameters:
        path: Root path containing a subfolder with TIFFs.
        mode: 'R' for raw single-channel, 'M' for merged RGB, etc.

    Returns:
        List of image groups (each a list of file paths).
    """
    sub_folders = [entry.name for entry in os.scandir(path) if entry.is_dir()]
    if not sub_folders:
        raise ValueError(f"No subdirectories found in {path}")
    sub_folder = sub_folders[0]

    file_paths = [
        os.path.join(path, sub_folder, file_name)
        for file_name in sorted(os.listdir(os.path.join(path, sub_folder)))
        if f"_{mode}_" in file_name and file_name.endswith(".TIF")
    ]

    # Only reshape for raw 4-channel grouping
    if mode == "R":
        image_groups = np.array(file_paths).reshape(-1, 4)
        return image_groups.tolist()
    else:
        return [[f] for f in file_paths]


def create_channel_mapping(
    image_group: List[str],
    channel_names: Tuple[str, ...] = ("dapi", "gfp", "tx_red", "cy5"),
) -> Tuple[str, str, Dict[str, str]]:
    if len(image_group) != len(channel_names):
        raise ValueError(
            f"Mismatch between number of channels ({len(channel_names)}) \
            and number of image files ({len(image_group)})."
        )

    # Extract metadata from the first file
    first_file = os.path.basename(image_group[0])
    image_info = first_file.split("_")[-1]
    well = image_info[0:3]
    well_fov_id = image_info[4:6]

    channel_dict = dict(zip(channel_names, image_group))
    return well, well_fov_id, channel_dict
