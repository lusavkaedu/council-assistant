import os
import shutil
from pathlib import Path

SOURCE_ROOT = Path("data/council_documents/committees")
TARGET_ROOT = Path("data/council_documents_flattened")

def main():
    print("🔎 Scanning for committee folders to flatten...")

    if not SOURCE_ROOT.exists():
        print(f"❌ Source folder not found: {SOURCE_ROOT}")
        return

    for committee_folder in SOURCE_ROOT.iterdir():
        if committee_folder.is_dir():
            new_path = TARGET_ROOT / committee_folder.name
            print(f"📁 Copying: {committee_folder} ➜ {new_path}")
            shutil.copytree(committee_folder, new_path, dirs_exist_ok=True)

    # Copy other top-level folders: cabinet, full_council, etc.
    for top_level in Path("data/council_documents").iterdir():
        if top_level.is_dir() and top_level.name != "committees":
            dest = TARGET_ROOT / top_level.name
            print(f"📁 Copying: {top_level} ➜ {dest}")
            shutil.copytree(top_level, dest, dirs_exist_ok=True)

    print("✅ Done. Flattened structure saved under:", TARGET_ROOT)

if __name__ == "__main__":
    main()