from typing import Dict, List, Tuple

import numpy as np


def compute_intensity_range(
    fovs: List[np.ndarray],
    method: str = "minmax",
    lower_pct: float = 1.0,
    upper_pct: float = 99.0,
) -> Tuple[Dict[int, float], Dict[int, float]]:
    """
    Computes global min/max or percentile-based intensity ranges per channel.

    Parameters:
        fovs: List of image stacks (C, H, W)
        method: 'minmax' or 'percentile'
        lower_pct: Lower percentile (if using 'percentile' method)
        upper_pct: Upper percentile

    Returns:
        Tuple of Dicts: min_vals[channel], max_vals[channel]
    """
    if method not in {"minmax", "percentile"}:
        raise ValueError(
            f"Invalid method '{method}'. Must be 'minmax' or 'percentile'."
        )

    min_per_channel = {}
    max_per_channel = {}

    for img_stack in fovs:
        for i in range(img_stack.shape[0]):
            img = img_stack[i]
            if method == "percentile":
                cur_min = np.percentile(img, lower_pct)
                cur_max = np.percentile(img, upper_pct)
            else:
                cur_min = img.min()
                cur_max = img.max()

            min_per_channel[i] = min(min_per_channel.get(i, cur_min), cur_min)
            max_per_channel[i] = max(max_per_channel.get(i, cur_max), cur_max)

    return min_per_channel, max_per_channel


def normalize_image_stack(
    img_stack: np.ndarray,
    min_vals: Dict[int, float],
    max_vals: Dict[int, float],
    to_uint8: bool = False,
) -> np.ndarray:
    """
    Applies per-channel normalization to an image stack.

    Parameters:
        img_stack: A single image stack (C, H, W)
        min_vals: Dict mapping channel index to minimum value
        max_vals: Dict mapping channel index to maximum value
        to_uint8: If True, normalize to [0, 255] and cast to np.uint8

    Returns:
        Normalized image stack of same shape (as float32 or uint8)
    """
    c, h, w = img_stack.shape
    out_dtype = np.uint8 if to_uint8 else np.float32
    out = np.empty((c, h, w), dtype=out_dtype)

    for i in range(c):
        img = img_stack[i]
        min_val = min_vals[i]
        max_val = max_vals[i]

        norm = (img - min_val) / (max_val - min_val + 1e-8)
        norm = np.clip(norm, 0, 1)
        if to_uint8:
            norm = (norm * 255).astype(np.uint8)
        out[i] = norm

    return out
