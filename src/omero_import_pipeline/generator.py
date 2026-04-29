import os
import uuid
from typing import Dict, List

from ome_types import OME, to_xml
from ome_types.model import (
    Channel,
    Image,
    ImageRef,
    LightPath,
    NamingConvention,
    Pixels,
    Pixels_DimensionOrder,
    PixelType,
    Plane,
    Plate,
    TiffData,
    Well,
    WellSample,
)

from omero_import_pipeline.templates import (
    DEFAULT_CHANNEL_NAMES,
    DIMENSION_ORDER,
    FIELDS_PER_WELL,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    NUM_COLUMNS,
    NUM_ROWS,
    PIXEL_TYPE,
    SAMPLES_PER_PIXEL,
)


def create_wells(
    num_images: int, num_rows: int = NUM_ROWS, num_columns: int = NUM_COLUMNS
) -> List[Well]:
    wells = []
    image_id = 0
    for row_index in range(num_rows):
        for column_index in range(num_columns):
            well_samples = []
            for field_index in range(FIELDS_PER_WELL):
                if image_id >= num_images:
                    break
                sample = WellSample(
                    id=f"WellSample:{row_index}:{column_index}:{field_index}",
                    index=image_id,
                    image_ref=ImageRef(id=f"Image:{image_id}"),
                )
                well_samples.append(sample)
                image_id += 1
            if well_samples:
                well = Well(
                    id=f"Well:{row_index}:{column_index}",
                    row=row_index,
                    column=column_index,
                    well_samples=well_samples,
                )
                wells.append(well)
        if image_id >= num_images:
            break
    return wells


def create_images(
    key_to_img_grp: Dict[str, List[str]], channel_names_per_img: List[List[str]]
) -> List[Image]:
    images = []
    for i, key in enumerate(key_to_img_grp.keys()):
        channels, tiff_data_blocks, planes = [], [], []
        file_name = key if key.endswith(".ome.tiff") else f"{key}.ome.tiff"
        uuid_str = f"urn:uuid:{uuid.uuid4()}"
        for ch_index, ch_name in enumerate(channel_names_per_img[i]):
            channels.append(
                Channel(
                    id=f"Channel:{i}:{ch_index}",
                    name=ch_name,
                    samples_per_pixel=SAMPLES_PER_PIXEL,
                    light_path=LightPath(),
                )
            )
            tiff_data_blocks.append(
                TiffData(
                    first_c=ch_index,
                    first_t=0,
                    first_z=0,
                    ifd=ch_index,
                    plane_count=1,
                    uuid=TiffData.UUID(file_name=file_name, value=uuid_str),
                )
            )
            planes.append(Plane(the_c=ch_index, the_t=0, the_z=0))
        pixels = Pixels(
            id=f"Pixels:{i}",
            type=PixelType(PIXEL_TYPE),
            size_x=IMAGE_WIDTH,
            size_y=IMAGE_HEIGHT,
            size_c=len(channel_names_per_img[i]),
            size_z=1,
            size_t=1,
            big_endian=False,
            dimension_order=Pixels_DimensionOrder(DIMENSION_ORDER),
            channels=channels,
            tiff_data_blocks=tiff_data_blocks,
            planes=planes,
        )
        images.append(Image(id=f"Image:{i}", name=key, pixels=pixels))
    return images


def create_ome_metadata(
    key_to_img_grp: Dict[str, List[str]], output_dir: str, plate_name: str = None
) -> str:
    plate_name = plate_name or os.path.basename(output_dir)
    images = create_images(
        key_to_img_grp, [DEFAULT_CHANNEL_NAMES] * len(key_to_img_grp)
    )
    wells = create_wells(num_images=len(images))
    plates = [
        Plate(
            id="Plate:0",
            name=plate_name,
            column_naming_convention=NamingConvention("number"),
            row_naming_convention=NamingConvention("letter"),
            columns=NUM_COLUMNS,
            rows=NUM_ROWS,
            wells=wells,
        )
    ]
    ome = OME(plates=plates, images=images)
    metadata_xml = to_xml(ome)

    metadata_file_name = f"{plate_name}.companion.ome"
    metadata_file_path = os.path.join(output_dir, metadata_file_name)
    with open(metadata_file_path, "w") as f:
        f.write(metadata_xml)

    return metadata_file_name
