import os
import shutil
import re

ROOT_DIR = "data/council_documents"
INCLUDE_TOPLEVEL = ["committees", "cabinet", "full_council"]

# Two date formats: YYYYMMDD and DDMMYYYY
ymd_pattern = re.compile(r"\b(20\d{2})[-_\.]?(0[1-9]|1[0-2])[-_\.]?(0[1-9]|[12]\d|3[01])\b")
dmy_pattern = re.compile(r"\b(0[1-9]|[12]\d|3[01])[-_\.]?(0[1-9]|1[0-2])[-_\.]?(20\d{2})\b")

def find_and_relocate():
    for top in INCLUDE_TOPLEVEL:
        top_dir = os.path.join(ROOT_DIR, top)
        for root, _, files in os.walk(top_dir):
            for file in files:
                full_path = os.path.join(root, file)

                # Skip already sorted
                if "originals" in root or "text_chunks" in root or "tables" in root:
                    continue

                # Try YYYY-MM-DD pattern first
                match = ymd_pattern.search(file)
                if match:
                    date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                else:
                    # Try DD-MM-YYYY pattern
                    alt = dmy_pattern.search(file)
                    if alt:
                        date_str = f"{alt.group(3)}-{alt.group(2)}-{alt.group(1)}"
                    else:
                        print(f"⚠️  Skipping (no date): {file}")
                        continue

                relative = os.path.relpath(root, start=ROOT_DIR)
                path_parts = relative.split(os.sep)

                # Skip if already inside a date folder
                if path_parts[-1].startswith("20"):
                    continue

                base_path = path_parts[:]
                meeting_folder = os.path.join(ROOT_DIR, *base_path, date_str)
                originals_folder = os.path.join(meeting_folder, "originals")
                os.makedirs(originals_folder, exist_ok=True)

                dest_path = os.path.join(originals_folder, file)
                if os.path.exists(dest_path):
                    print(f"🔁 Already exists: {file}")
                    continue

                shutil.move(full_path, dest_path)
                print(f"✅ Moved {file} -> {originals_folder}")

if __name__ == "__main__":
    find_and_relocate()
