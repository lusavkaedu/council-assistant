import pdfplumber
import re

def parse_decision_pdf(filepath):
    try:
        with pdfplumber.open(filepath) as pdf:
            if not pdf.pages:
                return None
            text = pdf.pages[0].extract_text()
            if not text:
                return None
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]

    data = {
        "filename": filepath.name,
        "from": [],
        "to": "",
        "decision_no": [],
        "subject": "",
        "key_decision": False,
        "classification": "",
        "past_pathway": "",
        "future_pathway": "",
        "electoral_division": "",
        "summary": "",
        "recommendation": "",
        "contact_officer": [],
        "relevant_director": {},
        "background_documents": [],
        "appendix_links": []
    }

    current_key = None
    buffer = []

    label_map = {
        "from:": "from",
        "by:": "from",
        "to:": "to",
        "decision no:": "decision_no",
        "subject:": "subject",
        "classification:": "classification",
        "past pathway of paper:": "past_pathway",
        "future pathway of paper:": "future_pathway",
        "electoral division:": "electoral_division",
        "summary:": "summary",
        "recommendation(s):": "recommendation",
        "recommendation:": "recommendation"
    }

    def flush_buffer():
        if current_key and buffer:
            text_block = " ".join(buffer).strip()
            text_block = re.sub(r"\s{2,}", " ", text_block)
            if current_key == "from":
                data[current_key].extend([line.strip() for line in text_block.split("\n") if line.strip()])
            elif current_key == "decision_no":
                data[current_key].extend(re.split(r"[,|and]\s*", text_block))
            else:
                if current_key == "summary":
                    text_block = re.sub(r"\bFOR (DECISION|INFORMATION)\b", "", text_block, flags=re.I).strip()
                data[current_key] = text_block

    for i, line in enumerate(lines):
        lower = line.lower()

        if "key decision" in lower or "for decision" in lower:
            data["key_decision"] = True
            continue

        matched = False
        for label, key in label_map.items():
            if lower.startswith(label):
                flush_buffer()
                current_key = key
                buffer = [line[len(label):].strip()]
                matched = True
                break

        if re.search(r"https?://", line):
            url = line.strip()
            data["appendix_links"].append(url)
            continue

        if re.match(r"(?i)^appendix|background document", line):
            data["background_documents"].append(line.strip())
            continue

        if "contact officer:" in lower:
            flush_buffer()
            current_key = None
            officer = {"name": "", "title": "", "email": "", "tel": ""}
            for subline in lines[i+1:i+6]:
                if "@" in subline:
                    officer["email"] = subline.strip()
                elif "tel:" in subline.lower():
                    officer["tel"] = re.sub(r"(?i)^tel:\s*", "", subline.strip())
                elif not officer["name"]:
                    officer["name"] = subline.strip()
                elif not officer["title"]:
                    officer["title"] = subline.strip()
            data["contact_officer"].append(officer)
            continue

        if "relevant director:" in lower:
            flush_buffer()
            current_key = None
            director = {"name": "", "title": "", "email": "", "tel": ""}
            for subline in lines[i+1:i+6]:
                if "@" in subline:
                    director["email"] = subline.strip()
                elif "tel:" in subline.lower():
                    director["tel"] = re.sub(r"(?i)^tel:\s*", "", subline.strip())
                elif not director["name"]:
                    director["name"] = subline.strip()
                elif not director["title"]:
                    director["title"] = subline.strip()
            data["relevant_director"] = director
            continue

        if not matched and re.match(r"^members? (are|is) asked to\b", lower):
            if not data["recommendation"]:
                data["recommendation"] = line.strip()
            continue

        if not matched and current_key:
            buffer.append(line)

    flush_buffer()

    if not data["contact_officer"]:
        for i in range(len(lines) - 1, -1, -1):
            if re.search(r"@[a-z]", lines[i]) or "ext:" in lines[i].lower():
                name_guess = lines[i - 1] if i > 0 else ""
                title_guess = lines[i - 2] if i > 1 else ""
                phone = re.sub(r"(?i)^ext:\s*", "", lines[i])
                data["contact_officer"].append({
                    "name": name_guess.strip(),
                    "title": title_guess.strip(),
                    "email": lines[i].strip() if "@" in lines[i] else "",
                    "tel": phone.strip() if "@" not in lines[i] else ""
                })
                break

    for key in data:
        if isinstance(data[key], str):
            data[key] = re.sub(r"\s{2,}", " ", data[key]).strip()
        elif isinstance(data[key], list):
            data[key] = [re.sub(r"\s{2,}", " ", item).strip() for item in data[key]]

    return data