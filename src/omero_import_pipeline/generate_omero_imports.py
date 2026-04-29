import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def load_mapping(path: Path) -> Dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_mapping(path: Path, mapping: Dict) -> None:
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2)


def create_screen(prefix: str) -> int:
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "-u",
            "omero-server",
            "omero-omeroserver-1",
            "/opt/omero/server/OMERO.server/bin/omero",
            "obj",
            "new",
            "Screen",
            f"name={prefix}",
            "-s",
            "localhost",
            "-u",
            "$omero_user",
            "-w",
            "$omero_password",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    screen_line = result.stdout.strip()
    if screen_line.startswith("Screen:"):
        screen_id = int(screen_line.split(":")[1])
        print(f"Created new screen '{prefix}' with ID {screen_id}")
        return screen_id
    raise RuntimeError(f"Unexpected screen creation output: {screen_line}")


def get_or_create_screen_id(prefix: str, mapping: Dict, mapping_path: Path) -> int:
    if prefix in mapping:
        return mapping[prefix]
    screen_id = create_screen(prefix)
    mapping[prefix] = screen_id
    save_mapping(mapping_path, mapping)
    return screen_id


def group_plates_by_prefix(plate_dirs: List[Path]) -> Dict[str, List[str]]:
    grouped = defaultdict(list)
    for plate_path in plate_dirs:
        prefix = plate_path.name[:4]
        grouped[prefix].append(str(plate_path))
    return grouped


def emit_omero_import_commands(
    grouped: Dict[str, List[str]],
    mapping: Dict,
    mapping_path: Path,
    omero_user: str,
    container_image_root: str,
    screen_id_override: int | None = None,
    max_plates: int = 10,
) -> List[str]:
    commands = []
    for prefix, plate_list in grouped.items():
        screen_id = (
            screen_id_override
            if screen_id_override is not None
            else get_or_create_screen_id(prefix, mapping, mapping_path)
        )
        for i in range(0, len(plate_list), max_plates):
            batch = plate_list[i : i + max_plates]

            batch_mapped = [
                f"{container_image_root}/{Path(p).parent.name}/{Path(p).name}"
                for p in batch
            ]

            command = (
                f"docker exec -it -u omero-server omero-omeroserver-1 "
                f"/opt/omero/server/OMERO.server/bin/omero import -s localhost "
                f"-u {omero_user} --target=Screen:{screen_id} " + " ".join(batch_mapped)
            )
            commands.append(command)
    return commands

def main():
    parser = argparse.ArgumentParser(
        description="Generate OMERO import commands for a directory of plates."
    )
    parser.add_argument("input_dir", help="Directory containing plate folders")
    parser.add_argument("mapping", help="Path to screen_mapping.json file")
    parser.add_argument(
        "--output",
        default="omero_import_commands.txt",
        help="File to write OMERO import commands",
    )
    parser.add_argument(
    "--omero-user",
    default="deisingj",
    help="OMERO username to embed in generated import commands",
    )
    parser.add_argument(
        "--container-image-root",
        default="/omero_images",
        help="Path prefix inside the OMERO container for imported images",
    )
    parser.add_argument(
    "--screen-id-override",
    type=int,
    default=None,
    help="If set, use this screen ID for all generated import commands",
    )
    args = parser.parse_args()

    base_path = Path(args.input_dir)
    mapping_path = Path(args.mapping)
    output_path = Path(args.output)

    if not base_path.exists():
        raise FileNotFoundError(f"Input directory not found: {base_path}")

    plate_dirs = [p for p in base_path.iterdir() if p.is_dir()]
    mapping = load_mapping(mapping_path)
    grouped = group_plates_by_prefix(plate_dirs)
    commands = emit_omero_import_commands(
        grouped,
        mapping,
        mapping_path,
        omero_user=args.omero_user,
        container_image_root=args.container_image_root,
        screen_id_override=args.screen_id_override,
    )

    with open(output_path, "w") as f:
        for cmd in commands:
            f.write(cmd + "\n")

    print(f"Wrote {len(commands)} OMERO import commands to: {output_path}")


if __name__ == "__main__":
    main()
