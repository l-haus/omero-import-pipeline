import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from omero_import_pipeline.grouping import build_fov_dict
from omero_import_pipeline.io import get_ordered_paths, read_tiff_group, write_ome_tiff
from omero_import_pipeline.normalization import (
    compute_intensity_range,
    normalize_image_stack,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_or_cache_stack(
    key: str, paths: List[str], cache_dir: Path
) -> Tuple[np.ndarray, object]:
    cache_path = cache_dir / f"{key}.npy"
    if cache_path.exists():
        logging.debug(f"Loading from cache: {cache_path}")
        stack = np.load(cache_path)
        metadata = read_tiff_group(paths).metadata[0]
    else:
        logging.debug(f"Reading and caching: {cache_path}")
        group = read_tiff_group(paths)
        stack = group.data
        metadata = group.metadata[0] if group.metadata else None
        np.save(cache_path, stack)
    return stack, metadata


def compute_normalization_values(fovs) -> Tuple[Dict[int, float], Dict[int, float]]:
    logging.info("Computing global intensity range for normalization")
    stacks = []
    for fov in fovs.values():
        paths = get_ordered_paths(fov.channel_file_paths)
        stack = read_tiff_group(paths).data
        stacks.append(stack)
    return compute_intensity_range(stacks)


def process_fov(
    key: str,
    fov,
    output_path: Path,
    normalize: bool,
    min_vals: Dict[int, float],
    max_vals: Dict[int, float],
):
    try:
        paths = get_ordered_paths(fov.channel_file_paths)
        group = read_tiff_group(paths)
        stack = group.data
        metadata = group.metadata[0] if group.metadata else None

        if normalize:
            stack = normalize_image_stack(stack, min_vals, max_vals, to_uint8=True)

        file_name = f"{key}.ome.tiff"
        write_ome_tiff(file_name, stack, output_path, metadata, is_normalized=normalize)
    except Exception as e:
        logging.error(f"Failed to process {key}: {e}")


def generate_ome_tiffs(
    input_dir: str, output_dir: str, workers: int, normalize: bool = False
) -> None:
    logging.info(f"Using {workers} worker threads")
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    fovs = build_fov_dict(input_path)
    logging.info(f"Found {len(fovs)} FOVs")

    if normalize:
        min_vals, max_vals = compute_normalization_values(fovs)
    else:
        min_vals, max_vals = {}, {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                process_fov,
                key,
                fov,
                output_path,
                normalize,
                min_vals,
                max_vals,
            )
            for key, fov in fovs.items()
        ]
        for f in as_completed(futures):
            f.result()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OME-TIFFs from raw microscopy TIFFs."
    )
    parser.add_argument(
        "input_dir", help="Input directory with raw TIFFs (nested folder structure)"
    )
    parser.add_argument("output_dir", help="Output directory for OME-TIFFs")
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel workers (default: number of CPU cores)",
    )
    parser.add_argument("--normalize", action="store_true", help="Normalize to uint8")

    args = parser.parse_args()
    generate_ome_tiffs(args.input_dir, args.output_dir, args.workers, args.normalize)


if __name__ == "__main__":
    main()
