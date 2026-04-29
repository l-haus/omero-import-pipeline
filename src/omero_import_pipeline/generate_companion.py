import argparse
import sys
from pathlib import Path

from omero_import_pipeline.generator import create_ome_metadata


def main():
    parser = argparse.ArgumentParser(
        description="Generate OME-XML companion file for a directory \
                    of .ome.tiff files."
    )
    parser.add_argument("input_dir", help="Directory containing .ome.tiff files")
    parser.add_argument(
        "--plate", help="Optional plate name (defaults to folder name)", default=None
    )
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    if not input_path.is_dir():
        print(f"Error: Input path {input_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Only include *.ome.tiff files
    ome_tiff_files = sorted(input_path.glob("*.ome.tiff"))
    if not ome_tiff_files:
        print(f"Error: No .ome.tiff files found in {input_path}", file=sys.stderr)
        sys.exit(1)

    # Prepare mapping: key -> list of 1 file (we don't group here)
    key_to_img_grp = {
        Path(f).stem.replace(".ome", ""): [str(f)] for f in ome_tiff_files
    }

    create_ome_metadata(
        key_to_img_grp=key_to_img_grp,
        output_dir=str(input_path),
        plate_name=args.plate,
    )
