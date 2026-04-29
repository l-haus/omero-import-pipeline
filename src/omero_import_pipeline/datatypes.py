from dataclasses import dataclass
from typing import Dict, List, Union

import numpy as np


@dataclass(frozen=True)
class FieldOfView:
    well: str
    well_fov_id: str
    channel_file_paths: Dict[str, str]


@dataclass
class OMEImageMetadata:
    well: Union[str, None]
    channel_name: Union[str, None]
    exposure_time: Union[float, None]  # seconds
    ome_uuid: Union[str, None]


@dataclass
class ImageGroup:
    data: np.ndarray  # shape: (C, H, W)
    metadata: List[OMEImageMetadata]  # one per channel
