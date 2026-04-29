import xml.etree.ElementTree as ET

import tifffile

from omero_import_pipeline.datatypes import OMEImageMetadata


def extract_ome_metadata(tiff_path: str) -> OMEImageMetadata:
    with tifffile.TiffFile(tiff_path) as tif:
        xml = tif.pages[0].description

    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return OMEImageMetadata(None, None, None, None)

    ns = {"ome": "http://www.openmicroscopy.org/Schemas/OME/2015-01"}

    def find(tag):
        return root.find(f".//ome:{tag}", ns)

    try:
        well_el = find("Well")
        row = int(well_el.attrib["Row"])
        col = int(well_el.attrib["Column"])
        well = chr(ord("A") + row) + str(col + 1).zfill(2)
    except Exception:
        well = None

    try:
        image_el = find("Image")
        channel_name = image_el.attrib.get("Name")
    except Exception:
        channel_name = None

    try:
        plane = find("Plane")
        exposure = float(plane.attrib.get("ExposureTime", 0.0))
        unit = plane.attrib.get("ExposureTimeUnit", "s")
        if unit == "ms":
            exposure /= 1000
    except Exception:
        exposure = None

    try:
        uuid = root.attrib.get("UUID", None)
    except Exception:
        uuid = None

    return OMEImageMetadata(
        well=well, channel_name=channel_name, exposure_time=exposure, ome_uuid=uuid
    )
