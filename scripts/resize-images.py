#!/usr/bin/env python3
"""Resize all images in a directory in place, keeping a .bak copy of each original.

Usage: resize-images.py <directory> [percent]   (percent defaults to 50)
"""
import shutil
import sys
from pathlib import Path

from PIL import Image

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def resize(path: Path, scale: float) -> None:
    backup = path.with_name(path.name + ".bak")
    if backup.exists():
        # Don't clobber the original from a previous run with an already-resized copy.
        print(f"skip {path.name}: {backup.name} already exists")
        return
    shutil.copy2(path, backup)

    with Image.open(path) as img:
        fmt = img.format
        exif = img.info.get("exif")
        icc = img.info.get("icc_profile")
        new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)

    save_args = {}
    if exif:
        save_args["exif"] = exif
    if icc:
        save_args["icc_profile"] = icc
    if fmt == "JPEG":
        save_args["quality"] = 90
    resized.save(path, format=fmt, **save_args)
    print(f"{path.name}: {img.width}x{img.height} -> {new_size[0]}x{new_size[1]}")


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__.strip())
    directory = Path(sys.argv[1])
    scale = (float(sys.argv[2]) if len(sys.argv) == 3 else 50) / 100
    if not directory.is_dir():
        sys.exit(f"not a directory: {directory}")

    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            resize(path, scale)


if __name__ == "__main__":
    main()
