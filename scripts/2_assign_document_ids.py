import argparse
import hashlib
import json
import os
import shutil
import uuid
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from PyPDF2 import PdfReader
from tqdm import tqdm
import jsonlines

# === CONFIGURATION ===
BASE_DIR = Path("data/council_documents")
REGISTER_PATH = Path("data/processed_register/document_ids.json")
MANIFEST_PATH = Path("data/processed_register/document_manifest.jsonl")
DELETION_LOG_PATH = Path("data/processed_register/deletion_log.jsonl")
RAW_METADATA_PATH = Path("data/document_metadata/raw_scraped_metadata.jsonl")

def report_folder_stats(stage_label):
    from datetime import datetime
    all_pdfs = list(BASE_DIR.rglob("originals/*.pdf"))
    total_size = sum(f.stat().st_size for f in all_pdfs)
    folder_count = len({f.parent for f in all_pdfs})
    summary = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage_label,
        "total_files": len(all_pdfs),
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "folder_count": folder_count
    }
    print(f"📊 Stage: {stage_label} — Files: {summary['total_files']}, Size: {summary['total_size_mb']} MB, Folders: {summary['folder_count']}")
    return summary

def log_deletion(filename, reason, kept=None):
    DELETION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "filename": filename,
        "reason": reason,
        "kept": kept,
        "deleted_at": Path().cwd().as_posix()
    }
    with open(DELETION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def fix_url_whitespace():
    for meta_path in BASE_DIR.rglob("metadata.json"):
        with meta_path.open("r", encoding="utf-8") as f:
            try:
                metadata = json.load(f)
            except json.JSONDecodeError:
                continue

        modified = False
        for entry in metadata:
            url = entry.get("url")
            if url and " " in url:
                from urllib.parse import quote
                if "?" in url:
                    url_base, query = url.split("?", 1)
                    entry["url"] = f"{quote(url_base, safe='/')}?{query}"
                else:
                    entry["url"] = quote(url, safe="/:")
                modified = True

        if modified:
            with meta_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

def consolidate_meeting_metadata():
    RAW_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    consolidated = []

    for meta_path in BASE_DIR.rglob("metadata.json"):
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for entry in data:
                    entry["source_metadata_file"] = str(meta_path.relative_to(BASE_DIR))
                    entry["scraped"] = True
                    consolidated.append(entry)
        except Exception as e:
            print(f"⚠️ Could not read {meta_path}: {e}")

    if not consolidated:
        print("⚠️ No metadata found to consolidate. Aborting.")
        return

    with jsonlines.open(RAW_METADATA_PATH, "w") as writer:
        for entry in consolidated:
            writer.write(entry)
    print(f"✅ Consolidated {len(consolidated)} metadata entries.")

    # Now safe to delete
    deleted_files = []
    for meta_path in BASE_DIR.rglob("metadata.json"):
        try:
            meta_path.unlink()
            deleted_files.append(str(meta_path))
        except Exception as e:
            print(f"⚠️ Could not delete {meta_path}: {e}")

    print(f"🗑️ Deleted {len(deleted_files)} old metadata.json files.")

def overwrite_path_fields():
    for meta_path in BASE_DIR.rglob("metadata.json"):
        with meta_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        modified = False
        for entry in metadata:
            c, d, fn = entry.get("committee"), entry.get("meeting_date"), entry.get("filename")
            if c and d and fn:
                new_path = f"{c}/{d}/originals/{fn}"
                if entry.get("path") != new_path:
                    entry["path"] = new_path
                    modified = True

        if modified:
            with meta_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

def tag_public_packs():
    if not RAW_METADATA_PATH.exists():
        print("⚠️ raw_scraped_metadata.jsonl not found — skipping public pack tagging.")
        return

    with jsonlines.open(RAW_METADATA_PATH, "r") as reader:
        metadata = list(reader)

    modified = False
    for entry in metadata:
        title = entry.get("title", "")
        filename = entry.get("filename", "")
        if (
            "public" in title.lower() and "pack" in title.lower()
        ) or (
            "public" in filename.lower() and "pack" in filename.lower()
        ):
            if entry.get("document_category") != "public_pack":
                entry["document_category"] = "public_pack"
                modified = True

    if modified:
        with jsonlines.open(RAW_METADATA_PATH, "w") as writer:
            for entry in metadata:
                writer.write(entry)
        print("🏷️ Tagged public pack documents in warehouse.")

def hash_file(pdf_path):
    try:
        reader = PdfReader(str(pdf_path))
        hasher = hashlib.sha256()
        for page in reader.pages:
            text = page.extract_text()
            if text:
                hasher.update(text.encode("utf-8"))
        return hasher.hexdigest()
    except:
        return None

def deduplicate_hashes():
    global summary_log
    with jsonlines.open(RAW_METADATA_PATH, "r") as reader:
        metadata = list(reader)

    hash_map = defaultdict(list)
    # Map from path to entry for fast lookup
    filename_to_entry = {entry["filename"]: entry for entry in metadata if "path" in entry}
    docid_map = {}
    for entry in metadata:
        if "path" in entry and "doc_id" in entry:
            docid_map[entry["path"]] = entry["doc_id"]

    updated_metadata = []

    for entry in tqdm(metadata, desc="🔍 Hashing PDFs"):
        rel_path = entry.get("path")
        if not rel_path:
            continue
        abs_path = BASE_DIR / rel_path
        if not abs_path.exists():
            continue
        h = hash_file(abs_path)
        if h:
            hash_map[h].append((abs_path, entry))

    print("📦 Finished hashing, now deduplicating identical files...")

    for h, files in hash_map.items():
        files.sort(key=lambda pair: ("_" in pair[0].stem, pair[0].name))
        keep_path, keep_entry = files[0]
        keep_entry["hash"] = h
        keep_entry["status"] = "ready_for_chunking"
        updated_metadata.append(keep_entry)

        survivor_doc_id = keep_entry.get("doc_id")
        # For any duplicates, mark as duplicate_removed and redirect_to survivor's doc_id
        for dupe_path, dupe_entry in files[1:]:
            dupe_entry["hash"] = h
            dupe_entry["status"] = "duplicate_removed"
            dupe_entry["redirect_to"] = survivor_doc_id
            # Do not overwrite existing doc_id
            updated_metadata.append(dupe_entry)
            try:
                dupe_path.unlink()
                log_deletion(str(dupe_path), reason="duplicate_hash", kept=keep_path.name)
            except:
                pass

    removed_count = sum(1 for e in updated_metadata if e.get("status") == "duplicate_removed")
    survivor_count = sum(1 for e in updated_metadata if e.get("status") == "ready_for_chunking")
    summary_log.append({
        "stage": "after_deduplicate_hashes",
        "duplicates_removed": removed_count,
        "unique_documents_retained": survivor_count
    })

    with jsonlines.open(RAW_METADATA_PATH, "w") as writer:
        for entry in updated_metadata:
            writer.write(entry)

## clean_filename_duplicates() function removed

def assign_doc_ids():
    # Always assign doc_ids to every metadata entry, before deduplication
    if REGISTER_PATH.exists():
        with REGISTER_PATH.open("r", encoding="utf-8") as f:
            doc_register = json.load(f)
    else:
        doc_register = {}

    with jsonlines.open(RAW_METADATA_PATH, "r") as reader:
        metadata = list(reader)

    updated_metadata = []
    for entry in tqdm(metadata, desc="🪪 Assigning doc_ids", unit="file"):
        path = entry.get("path")
        if not path:
            updated_metadata.append(entry)
            continue
        rel_path = Path(path)
        abs_path = BASE_DIR / rel_path
        if not abs_path.exists():
            updated_metadata.append(entry)
            continue
        # Assign a doc_id regardless of deduplication
        doc_id = entry.get("doc_id")
        if not doc_id:
            doc_id = f"doc_{uuid.uuid5(uuid.NAMESPACE_DNS, str(rel_path)).hex[:8]}"
        entry["doc_id"] = doc_id
        # Optionally, update doc_register for future reference
        doc_register[str(rel_path)] = {"id": doc_id}
        updated_metadata.append(entry)

    # Write back doc_ids to the metadata file for downstream use
    with jsonlines.open(RAW_METADATA_PATH, "w") as writer:
        for entry in updated_metadata:
            writer.write(entry)

    with REGISTER_PATH.open("w", encoding="utf-8") as f:
        json.dump(doc_register, f, indent=2, ensure_ascii=False)

def enrich_pdf_metadata():
    if not RAW_METADATA_PATH.exists():
        print("⚠️ Metadata warehouse not found. Skipping enrichment.")
        return

    with jsonlines.open(RAW_METADATA_PATH, "r") as reader:
        entries = list(reader)

    updated = []

    for entry in tqdm(entries, desc="📄 Enriching PDF metadata", unit="file"):
        rel_path = entry.get("path")
        if not rel_path:
            updated.append(entry)
            continue

        pdf_path = BASE_DIR / rel_path
        if not pdf_path.exists():
            updated.append(entry)
            continue

        try:
            reader = PdfReader(str(pdf_path))
            info = reader.metadata or {}
            entry["title"] = info.get("/Title", "")
            entry["author"] = info.get("/Author", "")
            entry["subject"] = info.get("/Subject", "")
            entry["keywords"] = info.get("/Keywords", "")
            entry["producer"] = info.get("/Producer", "")
            entry["creator"] = info.get("/Creator", "")
            entry["creation_date"] = info.get("/CreationDate", "")
            entry["mod_date"] = info.get("/ModDate", "")
            entry["num_pages"] = len(reader.pages)
        except Exception as e:
            print(f"⚠️ Failed to read metadata from {pdf_path.name}: {e}")

        updated.append(entry)

    with jsonlines.open(RAW_METADATA_PATH, "w") as writer:
        for record in updated:
            writer.write(record)

    print("✅ PDF metadata enrichment complete.")

def remove_orphan_files():
    """Delete any PDFs in originals/ folders that are not represented in the raw metadata warehouse."""
    if not RAW_METADATA_PATH.exists():
        print("⚠️ Cannot check for orphans: raw metadata not found.")
        return

    # Gather all PDFs
    all_pdfs = set([str(p.relative_to(BASE_DIR)) for p in BASE_DIR.rglob("originals/*.pdf")])

    # Load metadata
    with jsonlines.open(RAW_METADATA_PATH, "r") as reader:
        metadata_paths = {entry.get("path", "").strip() for entry in reader if "path" in entry}

    # Identify orphans
    orphan_paths = sorted(all_pdfs - metadata_paths)
    print(f"🧹 Found {len(orphan_paths)} orphan PDFs to delete...")

    removed = 0
    for rel_path in orphan_paths:
        abs_path = BASE_DIR / rel_path
        if abs_path.exists():
            try:
                abs_path.unlink()
                log_deletion(str(abs_path), reason="orphan_untracked", kept=None)
                removed += 1
            except Exception as e:
                print(f"⚠️ Could not delete {abs_path}: {e}")

    print(f"🗑️ Deleted {removed} orphan PDFs.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["run_all", "reset"], default="run_all")
    args = parser.parse_args()

    if args.mode == "reset":
        if REGISTER_PATH.exists():
            REGISTER_PATH.unlink()
        if MANIFEST_PATH.exists():
            MANIFEST_PATH.unlink()
        print("🧹 Cleared register and manifest.")

    summary_log = []
    summary_log.append(report_folder_stats("initial"))

    print("🔧 Fixing URLs...")
    fix_url_whitespace()
    print("📁 Updating path fields...")
    overwrite_path_fields()
    print("📥 Consolidating meeting-level metadata into raw warehouse...")
    consolidate_meeting_metadata()
    summary_log.append(report_folder_stats("after_consolidation"))

    print("🪪 Assigning document IDs...")
    assign_doc_ids()
    summary_log.append(report_folder_stats("after_assign_doc_ids"))

    print("🧠 Enriching with PDF metadata...")
    enrich_pdf_metadata()
    summary_log.append(report_folder_stats("after_enrichment"))

    print("🏷️ Tagging public packs...")
    tag_public_packs()
    summary_log.append(report_folder_stats("after_tag_public_packs"))

    print("🔍 Starting hashing of PDFs...")
    deduplicate_hashes()
    summary_log.append(report_folder_stats("after_deduplicate_hashes"))

    remove_orphan_files()

    # === Final manifest creation ===
    manifest_entries = []
    with jsonlines.open(RAW_METADATA_PATH, "r") as reader:
        for entry in reader:
            if entry.get("status") in {"ready_for_chunking", "ready_for_embedding"}:
                manifest_entries.append(entry)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(MANIFEST_PATH, "w") as writer:
        for entry in manifest_entries:
            writer.write(entry)

    print(f"📄 Saved manifest with {len(manifest_entries)} entries → {MANIFEST_PATH}")

    # No longer cleaning messy suffix duplicates
    # print("🧼 Cleaning messy suffix duplicates...")
    # clean_filename_duplicates()
    # summary_log.append(report_folder_stats("after_clean_filename_dupes"))

    print("✅ All cleaning and ID assignment complete.")

    with open("data/processed_register/cleaning_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_log, f, indent=2)

    # Save a CSV version of the cleaning summary log
    import pandas as pd
    summary_df = pd.DataFrame(summary_log)
    summary_csv_path = Path("data/processed_register/cleaning_summary.csv")
    summary_df.to_csv(summary_csv_path, index=False)

    # === Move summary and log files to central log/ folder with timestamp ===
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    LOG_DIR = Path("log")
    LOG_DIR.mkdir(exist_ok=True)

    log_files = [
        (DELETION_LOG_PATH, f"deletion_log_{timestamp}.jsonl"),
        (Path("data/processed_register/cleaning_summary.json"), f"cleaning_summary_{timestamp}.json"),
        (Path("data/processed_register/cleaning_summary.csv"), f"cleaning_summary_{timestamp}.csv"),
    ]

    for src_path, target_name in log_files:
        if src_path.exists():
            target_path = LOG_DIR / target_name
            shutil.move(str(src_path), str(target_path))
            print(f"📦 Moved {src_path.name} → {target_path}")