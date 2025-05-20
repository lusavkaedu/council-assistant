import uuid
from pathlib import Path
import json
import jsonlines
from tqdm import tqdm

# Paths can optionally be parameterised
REGISTER_PATH = Path("data/processed_register/document_ids.json")
RAW_METADATA_PATH = Path("data/metadata/documents.jsonl")
BASE_DIR = Path(".")

def assign_doc_ids(register_path=REGISTER_PATH, raw_path=RAW_METADATA_PATH, base_dir=BASE_DIR):
    if register_path.exists():
        with register_path.open("r", encoding="utf-8") as f:
            doc_register = json.load(f)
    else:
        doc_register = {}

    with jsonlines.open(raw_path, "r") as reader:
        metadata = list(reader)

    updated_metadata = []
    for entry in tqdm(metadata, desc="🪪 Assigning doc_ids", unit="file"):
        path = entry.get("path")
        if not path:
            updated_metadata.append(entry)
            continue
        rel_path = Path(path)
        abs_path = base_dir / rel_path
        if not abs_path.exists():
            updated_metadata.append(entry)
            continue
        doc_id = entry.get("doc_id")
        if not doc_id:
            doc_id = f"doc_{uuid.uuid5(uuid.NAMESPACE_DNS, str(rel_path)).hex[:8]}"
        entry["doc_id"] = doc_id
        doc_register[str(rel_path)] = {"id": doc_id}
        updated_metadata.append(entry)

    with jsonlines.open(raw_path, "w") as writer:
        for entry in updated_metadata:
            writer.write(entry)

    with register_path.open("w", encoding="utf-8") as f:
        json.dump(doc_register, f, indent=2, ensure_ascii=False)

def get_document_category(filename):
    lower = filename.lower()
    keywords = {
        "public_pack": ["public reports pack"],
        "agenda_frontsheet": ["agenda", "front"],
        "agenda": ["agenda", "additional agenda", "agenda item"],
        "minutes": ["printed minutes", "cpp minutes", "minutes of previous", "minutes"],
        "questions": ["questions put", "answers to questions", "q&a"],
        "motion": ["motion", "mtld"],
        "amendment": ["amendment"],
        "budget": ["budget", "revenue plan"],
        "report": ["report", "covering report", "update"],
        "decision_response": ["response", "decision", "record of decision"],
        "strategy": ["strategy", "investment strategy", "capital strategy"],
        "plan": ["plan", "local plan", "delivery plan"],
        "policy": ["policy", "statement"],
        "consultation": ["consultation"],
        "prod": ["prod"],
        "eqia": ["eqia"],
        "eqia": ["map "],
        "performance": ["performance", "quarterly performance", "qpr"],
        "terms_of_reference": ["terms of reference", "tor"],
        "supporting_material": ["glossary", "note", "you said we did"],
        "appendix": ["appendix", "annex"],
    }
    for category, patterns in keywords.items():
        if any(p in lower for p in patterns):
            return category
    return "other"