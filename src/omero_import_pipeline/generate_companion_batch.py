import argparse
import sys
from pathlib import Path

from omero_import_pipeline.generator import create_ome_metadata

def main():
    parser = argparse.ArgumentParser(
        description="Batch generate companion .ome files for multiple plate folders"
    )
    parser.add_argument("base_dir", help="Directory containing plate subfolders")
    parser.add_argument(
        "--list",
        help="Optional text file with plate folder names to include \
            Only subfolders listed in the file (one per line) will be processed. \
            Useful for partial or staged companion generation.",
        type=Path,
    )
    args = parser.parse_args()

    base_path = Path(args.base_dir)

    if not base_path.is_dir():
        print(f"Error: {base_path} is not a valid directory", file=sys.stderr)
        sys.exit(1)

    if args.list:
        if not args.list.exists():
            print(f"Error: List file {args.list} does not exist", file=sys.stderr)
            sys.exit(1)
        with open(args.list) as f:
            selected = {line.strip() for line in f if line.strip()}
        plate_dirs = [
            base_path / name for name in selected if (base_path / name).is_dir()
        ]
    else:
        plate_dirs = [p for p in base_path.iterdir() if p.is_dir()]

    if not plate_dirs:
        print(f"No subfolders found in {base_path}", file=sys.stderr)
        sys.exit(1)

    for plate_dir in sorted(plate_dirs):
        ome_tiff_files = sorted(plate_dir.glob("*.ome.tiff"))
        if not ome_tiff_files:
            print(f"Error: No .ome.tiff files found in {plate_dir}", file=sys.stderr)
            continue

        key_to_img_grp = {
            Path(f).stem.replace(".ome", ""): [str(f)] for f in ome_tiff_files
        }

        print(f"Generating companion file for {plate_dir.name}...")

        try:
            create_ome_metadata(
                key_to_img_grp=key_to_img_grp,
                output_dir=str(plate_dir),
                plate_name=plate_dir.name,
            )
        except Exception as e:
            print(f"Error processing {plate_dir.name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
