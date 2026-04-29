import argparse
import logging
from pathlib import Path

from omero_import_pipeline.generate_ome_tiffs import generate_ome_tiffs

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Batch OME-TIFF generation")
    parser.add_argument(
        "input_root", help="Directory containing multiple plate folders"
    )
    parser.add_argument("output_root", help="Directory to write generated OME-TIFFs")
    parser.add_argument(
        "--normalize", action="store_true", help="Apply uint8 normalization"
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of threads per plate"
    )

    args = parser.parse_args()
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)

    for plate_dir in input_root.iterdir():
        if plate_dir.is_dir():
            logging.info(f"Processing plate: {plate_dir.name}")
            plate_output_dir = output_root / plate_dir.name
            generate_ome_tiffs(
                input_dir=str(plate_dir),
                output_dir=str(plate_output_dir),
                workers=args.workers,
                normalize=args.normalize,
            )


if __name__ == "__main__":
    main()
