from logic.gpt_context import build_ai_summary_context
from logic.gpt_prompt import build_user_prompt, get_system_prompt
import streamlit as st
import pandas as pd
import numpy as np
import faiss
import os
from datetime import datetime
from logic.formatting import format_agenda_item, format_pdf_document
from logic.load_data import load_static_dataframes

# Load all static dataframes once at the top
documents, scraped_meta, summaries, meetings, pdf_merged = load_static_dataframes()

# Page setup
st.set_page_config(page_title="Unified Search", layout="wide")

st.title("Search Council Records")

if "shared_query" not in st.session_state:
    st.session_state["shared_query"] = ""

query = st.text_input(
    "What are you looking for in council records?",
    value=st.session_state.get("shared_query", ""),
    key="shared_query",
    placeholder="Is Kent county council worried about its debt levels?"
)

# --- Session-controlled flag for query submission detection ---
if "last_submitted_query" not in st.session_state:
    st.session_state["last_submitted_query"] = ""
if "query_submitted" not in st.session_state:
    st.session_state["query_submitted"] = False

if query != st.session_state["last_submitted_query"]:
    st.session_state["last_submitted_query"] = query
    st.session_state["query_submitted"] = True

# Logic to clear main query input when set by AI Summary tab
if st.session_state.get("reset_main_query"):
    query = ""
    st.session_state["shared_query"] = ""
    st.session_state["reset_main_query"] = False

# Session setup
if "session_id" not in st.session_state:
    import uuid
    st.session_state["session_id"] = str(uuid.uuid4())


tabs = st.tabs(["Agenda Items", "Full PDFs", "AI Summary"])

with tabs[0]:
    # Only rerun logic if query_submitted is True
    if st.session_state.get("query_submitted", False):
        if query.strip():  # Only show content if there's an actual query
            from logic.semantic_search import search_agenda_items
            agenda_hits = search_agenda_items(query, max_k=50, threshold=1.5)
            # --- DEBUG: Show agenda_hits result count and preview ---
            st.info(f"🔍 Found {len(agenda_hits)} agenda matches")
            st.dataframe(agenda_hits.head(3))
            # Default sorting: by relevance (score)
            agenda_hits = agenda_hits.sort_values("score")

            # Format date with fallback if not int/float
            def safe_to_datetime(val):
                try:
                    if isinstance(val, (int, float)) and not pd.isnull(val):
                        return pd.to_datetime(int(val), unit="ms", errors="coerce").date()
                    elif isinstance(val, str):
                        return pd.to_datetime(val, errors="coerce").date()
                except Exception:
                    return pd.NaT
                return pd.NaT
            agenda_hits["meeting_date"] = agenda_hits["meeting_date"].apply(safe_to_datetime)

            # Clean up and format columns
            agenda_hits["Committee"] = agenda_hits["committee_id"].str.replace("_", " ").str.replace("-", " ").str.title()
            # Updated date formatting to short month
            agenda_hits["Meeting Date"] = agenda_hits["meeting_date"].apply(lambda d: d.strftime("%-d %b %Y") if pd.notnull(d) else "")

            # Load original agenda metadata to recover fields like item_title
            import jsonlines
            with jsonlines.open("data/metadata/agendas.jsonl", "r") as reader:
                agenda_meta = pd.DataFrame(reader)
                agenda_meta = agenda_meta.drop_duplicates(subset="agenda_id")

            # Join on agenda_id, include item_title, item_text, and pdf_urls
            agenda_hits = agenda_hits.merge(agenda_meta[["agenda_id", "item_title", "item_text", "pdf_urls"]], left_on="chunk_id", right_on="agenda_id", how="left")
            # Deduplicate by chunk_id after merging metadata
            agenda_hits = agenda_hits.drop_duplicates(subset="chunk_id")
            # Populate correct date format for agenda items
            # Use already parsed meeting_date
            agenda_hits["meeting_str"] = agenda_hits["meeting_date"].apply(lambda d: d.strftime("%b %Y") if pd.notnull(d) else "")

            # meetings already loaded at top
            # Merge web_meeting_code into agenda_hits
            agenda_hits = agenda_hits.merge(meetings[["meeting_id", "web_meeting_code"]], on="meeting_id", how="left")

            # Update Meeting Date to be a hyperlink if web_meeting_code is available
            agenda_hits["Meeting Date"] = agenda_hits.apply(
                lambda row: f'<a href="https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row["web_meeting_code"]}" target="_blank">{row["Meeting Date"]}</a>'
                if pd.notnull(row["web_meeting_code"]) and pd.notnull(row["Meeting Date"]) else row["Meeting Date"],
                axis=1
            )

            # Use preloaded pdf_merged and url_to_title
            url_to_title = pdf_merged.set_index("url")["item_title"].to_dict()

            # Use central formatter for agenda items
            agenda_hits["Agenda Item"] = [
                format_agenda_item(
                    row["item_title"],
                    row["item_text"],
                    row.get("pdf_urls", []),
                    pdf_merged
                )
                for _, row in agenda_hits.iterrows()
            ]

            st.write("### Previously Discussed:")
            display_df = agenda_hits[["Meeting Date", "Committee", "Agenda Item"]]
            st.markdown(display_df.head(10).to_html(escape=False, index=False), unsafe_allow_html=True)
        # Reset the trigger after handling in the first tab
    st.session_state["query_submitted"] = False
    
with tabs[1]:
    import jsonlines
    from openai import OpenAI

    @st.cache_data
    def load_pdf_warehouse():
        with jsonlines.open("data/metadata/pdf_warehouse.jsonl", "r") as reader:
            return pd.DataFrame(reader).drop_duplicates(subset="doc_id")

    pdf_data = load_pdf_warehouse()

    # --- Replacement block to match notebook implementation ---
    if query:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        query_vector = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding
        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)

        # Load FAISS index and metadata
        summary_index = faiss.read_index("data/embeddings/pdf_summaries/pdf_summary_index.faiss")
        with jsonlines.open("data/embeddings/pdf_summaries/metadata_pdf_summaries.jsonl", "r") as reader:
            summary_meta = pd.DataFrame(reader).drop_duplicates(subset="doc_id")

        D, I = summary_index.search(query_vector, 100)
        valid_indices = I[0][I[0] != -1]
        valid_indices = [i for i in valid_indices if i < len(summary_meta)]

        if valid_indices:
            faiss_subset = summary_meta.iloc[valid_indices].copy()
            faiss_subset["score"] = D[0][:len(faiss_subset)]

            # Merge with full metadata from summaries.jsonl
            # (we will merge the correct summaries after merging with pdf_data)
            results = faiss_subset.merge(pdf_data, on="doc_id", how="left")
        else:
            results = pd.DataFrame(columns=pdf_data.columns)
    else:
        results = pdf_data.copy()

    # Always merge in the true full summaries after merging with pdf_data
    import jsonlines
    with jsonlines.open("data/pdf_summaries/summaries.jsonl", "r") as reader:
        true_summaries = pd.DataFrame(reader)

    results = results.drop(columns=["summary"], errors="ignore")
    results = results.merge(true_summaries[["doc_id", "summary"]], on="doc_id", how="left")

    st.markdown("### Showing top 10 of matching documents")

    def get_meeting_str(raw_date):
        if pd.isnull(raw_date):
            return "N/A"
        try:
            return pd.to_datetime(int(raw_date), unit="ms").strftime("%b %Y")
        except Exception:
            return "N/A"

    def format_label(title, source_filename):
        if not isinstance(title, str) or pd.isnull(title):
            title = ""
        if not isinstance(source_filename, str) or pd.isnull(source_filename):
            return title or "Untitled"
        filename_simple = source_filename.rsplit(".", 1)[0]
        return f"{title} ({filename_simple})" if filename_simple.lower() not in title.lower() else title

    rows = []
    for _, row in results.head(10).iterrows():
        label = format_label(row.get("display_title_y"), row.get("source_filename"))
        date_str = get_meeting_str(row.get("meeting_date"))
        summary = row["summary"] if "summary" in row and pd.notnull(row["summary"]) else "No summary available."
        rows.append({
            "Document": label,
            "Date": date_str,
            "Summary": summary
        })

    final_df = pd.DataFrame(rows)
    st.markdown(final_df.to_html(escape=False, index=False), unsafe_allow_html=True)


with tabs[2]:
    question = st.session_state.get("shared_query", "")
    st.sidebar.markdown("### AI Summary Settings")
    top_k = st.sidebar.slider("Number of summaries to send to GPT", min_value=1, max_value=20, value=5)
    # Remove unused context_window slider for now
    # context_window = st.sidebar.slider("Adjacent summaries to include", min_value=0, max_value=3, value=1)
    temperature = st.sidebar.slider("GPT Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1)
    preview_chunks = st.button("Generate AI Summary")
    # Logic to clear main query input when a new question is submitted
    if preview_chunks and question:
        st.session_state["reset_main_query"] = True

    if preview_chunks and question.strip():
        with st.spinner("Generating summary..."):
            from openai import OpenAI
            import jsonlines
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            query_vector = client.embeddings.create(input=[question], model="text-embedding-3-small").data[0].embedding
            query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)

            # Load both indexes and metadata
            with jsonlines.open("data/embeddings/pdf_summaries/metadata_pdf_summaries.jsonl", "r") as reader:
                summaries_df = pd.DataFrame(reader)
                summaries_df = summaries_df.drop_duplicates(subset="doc_id")
            summary_index = faiss.read_index("data/embeddings/pdf_summaries/pdf_summary_index.faiss")
            summary_D, summary_I = summary_index.search(query_vector, 100)

            with jsonlines.open("data/embeddings/agendas/metadata_agenda.jsonl", "r") as reader:
                agenda_df = pd.DataFrame(reader)
                agenda_df = agenda_df.drop_duplicates(subset="chunk_id")
            agenda_index = faiss.read_index("data/embeddings/agendas/agenda_index.faiss")
            agenda_D, agenda_I = agenda_index.search(query_vector, 100)

            # Filter out invalid indices from FAISS results for summaries
            valid_summary_indices = summary_I[0][summary_I[0] != -1]
            valid_summary_indices = [i for i in valid_summary_indices if i < len(summaries_df)]
            summary_hits = summaries_df.iloc[valid_summary_indices].copy()
            summary_hits["score"] = summary_D[0][:len(summary_hits)]
            summary_hits["source_type"] = "pdf"

            # Filter out invalid indices from FAISS results for agendas
            valid_agenda_indices = agenda_I[0][agenda_I[0] != -1]
            valid_agenda_indices = [i for i in valid_agenda_indices if i < len(agenda_df)]
            agenda_hits = agenda_df.iloc[valid_agenda_indices].copy()
            agenda_hits["score"] = agenda_D[0][:len(agenda_hits)]
            agenda_hits["source_type"] = "agenda"

            # Always send 4 agenda items and 6 summaries
            agenda_hits = agenda_hits.sort_values("score").drop_duplicates(subset=["chunk_id"]).head(4)
            summary_hits = summary_hits.sort_values("score").drop_duplicates(subset=["doc_id"]).head(6)

            combined = pd.concat([agenda_hits, summary_hits], ignore_index=True)

            # Merge with document metadata for PDF summaries using unified pdf_warehouse
            from logic.load_data import load_pdf_warehouse
            pdf_warehouse = load_pdf_warehouse()
            pdf_combined = combined[combined["source_type"] == "pdf"]
            if not pdf_combined.empty:
                # Ensure doc_id is string and stripped before merging to prevent mismatches
                pdf_combined["doc_id"] = pdf_combined["doc_id"].astype(str).str.strip()
                pdf_warehouse["doc_id"] = pdf_warehouse["doc_id"].astype(str).str.strip()
                pdf_combined = pdf_combined.merge(
                    pdf_warehouse[["doc_id", "display_title", "url", "meeting_date", "source_filename"]],
                    on="doc_id",
                    how="left"
                )
                # Generate meeting_str from meeting_date for PDFs after merging
                def get_meeting_str(raw_date):
                    if pd.isnull(raw_date):
                        return "N/A"
                    try:
                        return pd.to_datetime(int(raw_date), unit="ms").strftime("%b %Y")
                    except Exception:
                        try:
                            return pd.to_datetime(raw_date).strftime("%b %Y")
                        except Exception:
                            return "N/A"
                if "meeting_date" in pdf_combined.columns:
                    pdf_combined["meeting_str"] = pdf_combined["meeting_date"].apply(get_meeting_str)

            # For agenda, get agenda metadata for item_title/text (use preloaded agenda_meta and meetings)
            with jsonlines.open("data/metadata/agendas.jsonl", "r") as reader:
                agenda_meta = pd.DataFrame(reader)
                agenda_meta = agenda_meta.drop_duplicates(subset="agenda_id")
            agenda_combined = combined[combined["source_type"] == "agenda"]
            if not agenda_combined.empty:
                agenda_combined = agenda_combined.merge(agenda_meta[["agenda_id", "item_title", "item_text"]], left_on="chunk_id", right_on="agenda_id", how="left")
                agenda_combined = agenda_combined.merge(meetings[["meeting_id", "web_meeting_code"]], on="meeting_id", how="left")

            # Recombine for context building
            all_combined = pd.concat([pdf_combined, agenda_combined], ignore_index=True, sort=False)
            all_combined = all_combined.sort_values("score")

            # Build GPT context using helper function
            context = build_ai_summary_context(question, pdf_combined, agenda_combined)

            prompt = build_user_prompt(question, context)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=temperature,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader("AI Summary")
                st.markdown(response.choices[0].message.content, unsafe_allow_html=True)

            with col2:
                st.subheader("Documents Used")
                # Always render 4 agenda items and 6 PDF summaries in that order
                pdf_links = all_combined[all_combined["source_type"] == "pdf"].head(6).copy()
                # Precompute meeting_str for PDFs (and agendas) just like agenda items
                def get_meeting_str(raw_date):
                    if pd.isnull(raw_date):
                        return "N/A"
                    try:
                        return pd.to_datetime(int(raw_date), unit="ms").strftime("%b %Y")
                    except Exception:
                        try:
                            return pd.to_datetime(raw_date).strftime("%b %Y")
                        except Exception:
                            return "N/A"
                # Use the correct date column for PDFs after merging
                pdf_links["meeting_str"] = pdf_links["meeting_date"].apply(get_meeting_str)
                agenda_links = all_combined[all_combined["source_type"] == "agenda"].head(4).copy()
                agenda_links["meeting_str"] = agenda_links["meeting_date"].apply(get_meeting_str)
                # Always use the correct label format for PDFs, even if meeting_str is empty
                for _, row in pd.concat([agenda_links, pdf_links]).iterrows():
                    url = None
                    title = ""
                    label = ""
                    if row["source_type"] == "pdf" and pd.notnull(row.get("url")):
                        url = row["url"]
                        # Use display_title if present, otherwise fallback to source_filename or doc_id
                        title = row.get("display_title") or row.get("source_filename") or row["doc_id"]
                        meeting_str = row.get("meeting_str", "")
                        label = f"{title} ({meeting_str})"
                    elif row["source_type"] == "agenda":
                        title = row.get("item_title", "Agenda Item")
                        web_meeting_code = row.get("web_meeting_code")
                        if pd.notnull(web_meeting_code):
                            url = f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={web_meeting_code}"
                        meeting_str = row.get("meeting_str", "")
                        label = f"Agenda Item: {title} ({meeting_str})"
                    if url:
                        st.markdown(f'<a href="{url}" target="_blank">{label}</a>', unsafe_allow_html=True)
                    elif label:
                        st.markdown(label)

            st.markdown("---")
            with st.expander("📤 What was sent to ChatGPT"):
                st.code(prompt, language="markdown")

st.markdown("---")
st.caption("Coming soon: Ask GPT, Save Search, and Alert Me features.")