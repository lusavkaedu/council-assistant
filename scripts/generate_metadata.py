import os
import json
import datetime
from pathlib import Path
import re

ROOT_DIR = "data/council_documents"
TARGET_SUBFOLDER = "originals"
CHUNK_SUFFIX = "_chunks.json"

CATEGORY_KEYWORDS = {
    "agenda": "agenda",
    "minutes": "minutes",
    "appendix": "appendix",
    "app": "appendix",
    "report": "report",
    "update": "report",
    "decision": "decision",
    "record": "decision",
    "dashboard": "dashboard",
    "policy": "policy",
    "questions": "q&a",
    "answers": "q&a"
}

def infer_category(filename: str) -> str:
    name = filename.lower()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in name:
            return category
    return "other"

def count_chunks(chunk_file_path: Path) -> int:
    try:
        with open(chunk_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0

def clean_title(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r"^\d{4}-\d{2}-\d{2}", "", name)       # Remove leading date
    name = re.sub(r"^\d{6}-\d{2}-\d{2}", "", name)       # Remove malformed numeric
    name = re.sub(r"^\d{4}-\d{2}", "", name)             # Remove year-month prefix
    name = re.sub(r"[_\-]", " ", name).strip()
    name = re.sub(r"\s{2,}", " ", name)
    return name.title()

def generate_metadata():
    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        if os.path.basename(dirpath) != TARGET_SUBFOLDER:
            continue

        parent_folder = Path(dirpath).parent
        meeting_date = parent_folder.name  # e.g. "2025-01-24"
        group = parent_folder.parent.name  # e.g. "asc", "cabinet", "full_council"

        metadata_file = parent_folder / "metadata.json"
        entries = []

        for file in filenames:
            full_path = Path(dirpath) / file
            stat = full_path.stat()
            name = file
            suffix = full_path.suffix.lower()

            entry = {
                "filename": name,
                "path": str(full_path.relative_to(parent_folder)),
                "size_kb": round(stat.st_size / 1024),
                "type": suffix[1:] if suffix.startswith(".") else suffix,
                "document_category": infer_category(name),
                "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "group": group,
                "meeting_date": meeting_date,
                "title": clean_title(name)
            }

            if suffix == ".pdf":
                base_name = full_path.stem
                chunk_path = full_path.parent / f"{base_name}{CHUNK_SUFFIX}"
                if chunk_path.exists():
                    entry["chunks"] = count_chunks(chunk_path)

            entries.append(entry)

        if entries:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
            print(f"✅ Updated {metadata_file}")

if __name__ == "__main__":
    generate_metadata()
