from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path


EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc"}
EXCLUDE_DIRS = {"output"}


def copy_clean(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in EXCLUDE_NAMES:
            continue
        if item.is_dir():
            if item.name in EXCLUDE_DIRS:
                continue
            copy_clean(item, dst / item.name)
            continue
        if item.suffix in EXCLUDE_SUFFIXES:
            continue
        shutil.copy2(item, dst / item.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--output", required=True, help="zip path")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    output_zip = Path(args.output).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        staging_root = Path(tmp) / skill_dir.name
        copy_clean(skill_dir, staging_root)
        archive_base = output_zip.with_suffix("")
        created = shutil.make_archive(str(archive_base), "zip", root_dir=staging_root.parent, base_dir=staging_root.name)
        created_path = Path(created)
        if created_path != output_zip:
            if output_zip.exists():
                output_zip.unlink()
            output_zip.write_bytes(created_path.read_bytes())
            created_path.unlink()
    print(output_zip)


if __name__ == "__main__":
    main()
