import streamlit as st
import json
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote
import difflib
from datetime import date

st.set_page_config(page_title="Glossary", layout="wide")
st.title("📘 Glossary of Terms")

query_params = st.query_params
preselect_term = query_params.get("term")
preselect_term = preselect_term if isinstance(preselect_term, str) else (preselect_term[0] if preselect_term else "")

# --- Load glossary
glossary_path = Path("data/glossary/glossary.json")
if not glossary_path.exists():
    st.error("Glossary file not found at: data/glossary/glossary.json")
    st.stop()

with glossary_path.open("r", encoding="utf-8") as f:
    glossary = json.load(f)

# Load metadata warehouse
metadata_path = Path("data/document_metadata/raw_scraped_metadata.jsonl")
doc_meta_map = {}
if metadata_path.exists():
    with metadata_path.open("r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if "filename" in record:
                doc_meta_map[record["filename"]] = {
                    "url": record.get("url", ""),
                    "date": record.get("meeting_date", ""),
                    "committee": record.get("committee", ""),
                    "category": record.get("document_category", ""),
                    "glossary_terms": record.get("glossary_terms", [])
                }

options = sorted([entry["term"] for entry in glossary])

with st.sidebar:
    st.header("📂 Filters")
    categories = sorted(set(entry.get("category", "Uncategorized") for entry in glossary))
    selected_categories = st.multiselect("Filter by category", categories)

    filtered_terms = [term for term in options if any(entry.get("category", "Uncategorized") in selected_categories for entry in glossary if entry["term"] == term)] if selected_categories else options
    select_options = [""] + sorted(filtered_terms)
    default_index = select_options.index(preselect_term) if preselect_term in select_options else 0
    selected_term = st.selectbox("Select a glossary term to view details", select_options, index=default_index)

    typed_term = st.text_input("🔍 Or type a term")
    if typed_term:
        typed_term_lower = typed_term.lower()
        matched_term = next(
            (
                entry["term"]
                for entry in glossary
                if all(token in (entry["term"] + " " + " ".join(entry.get("aliases", []))).lower() for token in typed_term_lower.split())
            ),
            None
        )
        if matched_term:
            selected_term = matched_term
        elif similar := difflib.get_close_matches(typed_term, options, n=3):
            st.warning(f"Term not found. Did you mean: {', '.join(similar)}?")
        else:
            st.warning("Term not found and no similar terms detected.")

    st.markdown("---")
    st.subheader("📄 Document Filters")

    max_docs = st.number_input("Number of documents to display", min_value=1, max_value=100, value=20)

    available_committees = sorted({meta["committee"] for meta in doc_meta_map.values() if meta["committee"]})
    selected_committee = st.selectbox("Committee", [""] + available_committees)

    available_doc_cats = sorted({meta["category"] for meta in doc_meta_map.values() if meta["category"]})
    selected_doc_cat = st.selectbox("Category", [""] + available_doc_cats)

    today = date.today()
    start_date = st.date_input("Start date", value=None)
    end_date = st.date_input("End date", value=today)

if selected_term:
    entry = next((e for e in glossary if e["term"] == selected_term), None)
    if entry:
        term = entry["term"]
        aliases = entry.get("aliases", [])
        definition = entry["definition"]
        category = entry.get("category", "Uncategorized")
        tooltip = entry.get("tooltip_short", "")
        doc_source = entry.get("source_doc", "")

        title = f"🔹 {term}"
        if aliases:
            title += f" = {', '.join(aliases)}"
        st.subheader(title)
        if tooltip:
            st.markdown(f"**In short:** {tooltip}")
        # st.markdown(f"**Category:** {category}")
        st.markdown(f"**Definition:** {definition}")
        if entry.get("related_terms"):
            related_terms = [t for t in entry['related_terms'] if t != term]
            if related_terms:
                st.markdown(f"**Related terms:** {', '.join(related_terms)}")
        source_url = doc_meta_map.get(doc_source, {}).get("url")
        if source_url:
            st.markdown(f"[📄 Related Glossary provided by the county]({source_url})")
        elif doc_source:
            file_path = Path("data/council_documents") / doc_source
            st.markdown(f"[📄 View local file]({file_path})")

        matching_docs = []
        search_phrases = [term.lower()] + [a.lower() for a in aliases]
        for fname, meta in list(doc_meta_map.items())[:1000]:
            doc_terms = meta.get("glossary_terms", [])
            doc_date = meta.get("date")
            if (
                any(t in doc_terms for t in [term] + aliases)
                and (not selected_committee or meta["committee"] == selected_committee)
                and (not selected_doc_cat or meta["category"] == selected_doc_cat)
                and (not start_date or (doc_date and doc_date >= str(start_date)))
                and (not end_date or (doc_date and doc_date <= str(end_date)))
            ):
                link = f"[{fname}]({meta['url']})" if meta["url"] else fname
                matching_docs.append({
                    "date": meta["date"],
                    "committee": meta["committee"],
                    "category": meta["category"],
                    "filename": link
                })

        matching_docs.sort(key=lambda x: x['date'], reverse=True)

        if matching_docs:
            st.markdown("**Documents mentioning this term:**")
            table_md = "| Date | Committee | Category | Filename |\n"
            table_md += "|------|-----------|----------|---------|\n"
            for doc in matching_docs[:max_docs]:
                link = doc["filename"]
                table_md += f"| {doc['date']} | {doc['committee']} | {doc['category']} | {link} |\n"
            st.markdown(table_md, unsafe_allow_html=True)

st.markdown("---")
st.caption("Showing glossary entries from data/glossary/glossary.json")
