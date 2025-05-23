import streamlit as st
import pandas as pd
import numpy as np
import faiss
import os
from datetime import datetime

# Load documents.jsonl
import jsonlines
with jsonlines.open("data/metadata/documents.jsonl", "r") as reader:
    documents = pd.DataFrame(reader)

# Load scraped_pdf_metadata.jsonl
with jsonlines.open("data/pdf_metadata/scraped_pdf_metadata.jsonl", "r") as reader:
    scraped_meta = pd.DataFrame(reader)

# Load summaries.jsonl
with jsonlines.open("data/pdf_summaries/summaries.jsonl", "r") as reader:
    summaries = pd.DataFrame(reader)

# Load meetings.jsonl
with jsonlines.open("data/metadata/meetings.jsonl", "r") as reader:
    meetings = pd.DataFrame(reader)

# Merge all on doc_id
pdf_merged = documents.merge(scraped_meta, on="doc_id", how="left")
pdf_merged = pdf_merged.merge(summaries, on="doc_id", how="left")
# Merge web_meeting_code into pdf_merged from meetings.jsonl
pdf_merged = pdf_merged.merge(meetings[["meeting_id", "web_meeting_code"]], on="meeting_id", how="left")
# Deduplicate by doc_id after all merges
pdf_merged = pdf_merged.drop_duplicates(subset="doc_id")

# Page setup
st.set_page_config(page_title="Unified Search", layout="wide")

st.title("Search Council Records")

if "shared_query" not in st.session_state:
    st.session_state["shared_query"] = ""

query = st.session_state["shared_query"]

# Logic to clear main query input when set by AI Summary tab
if st.session_state.get("reset_main_query"):
    query = ""
    st.session_state["shared_query"] = ""
    st.session_state["reset_main_query"] = False

# Session setup
if "session_id" not in st.session_state:
    import uuid
    st.session_state["session_id"] = str(uuid.uuid4())

# Sidebar Search Input
with st.sidebar:
    st.markdown("### Search Filters")
    max_docs_faiss = st.number_input("How many documents to retrieve from archive", min_value=10, max_value=200, value=50, step=10)
    sort_order = st.selectbox("Sort by", ["Relevance", "Date (newest first)", "Date (oldest first)", "Committee"])
    max_results = st.number_input("Max results to display", min_value=1, max_value=100, value=10, step=1)
    committees_available = ["All"] + sorted(pdf_merged["committee_name"].dropna().unique().tolist())
    selected_committee = st.selectbox("Committee", committees_available)
    start_date = st.date_input("Start date", value=(pd.to_datetime("today") - pd.Timedelta(days=365)), format="DD/MM/YYYY")
    end_date = st.date_input("End date", value=pd.Timestamp.today(), format="DD/MM/YYYY")
    # selected_type = st.multiselect("Document Type", ["Agenda", "Minutes", "Report", "EQIA", "Motions"])  # Used in Full PDFs tab
    st.markdown("---")

st.markdown("### Search Results")
tabs = st.tabs(["Agenda Items", "Full PDFs", "People", "AI Summary"])

with tabs[0]:
    new_query = st.text_input(
        "What are you looking for in council records?",
        value=st.session_state["shared_query"],
        placeholder="What is the latest council position on 20mph zones?",
        key="agenda_query"
    )
    if new_query != st.session_state["shared_query"]:
        st.session_state["shared_query"] = new_query
        query = new_query

    if query.strip():  # Only show content if there's an actual query
        # [Keep all the existing search and display logic here]
        import jsonlines
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Load metadata
        with jsonlines.open("data/embeddings/agendas/metadata_agenda.jsonl", "r") as reader:
            agenda_df = pd.DataFrame(reader)

        # Load FAISS index
        index = faiss.read_index("data/embeddings/agendas/agenda_index.faiss")

        # Prevent embedding errors when query is empty
        if query and query.strip():
            embedding = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding
            embedding = np.array(embedding, dtype=np.float32).reshape(1, -1)
            distances, indices = index.search(embedding, 100)
        else:
            distances, indices = np.array([]), np.array([[]])
        if distances.size > 0 and indices.size > 0:
            agenda_hits = agenda_df.iloc[indices[0]].copy()
            agenda_hits["score"] = distances[0]
        else:
            agenda_hits = agenda_df.head(0).copy()
            agenda_hits["score"] = []
        # Apply sorting based on sidebar selection
        if sort_order == "Relevance":
            agenda_hits = agenda_hits.sort_values("score")
        elif sort_order == "Date (newest first)":
            agenda_hits = agenda_hits.sort_values("meeting_date", ascending=False)
        elif sort_order == "Date (oldest first)":
            agenda_hits = agenda_hits.sort_values("meeting_date", ascending=True)
        elif sort_order == "Committee":
            agenda_hits = agenda_hits.sort_values("committee_id")

        # Format date
        agenda_hits["meeting_date"] = pd.to_datetime(agenda_hits["meeting_date"], unit="ms", errors="coerce").dt.date

        # Clean up and format columns
        agenda_hits["Committee"] = agenda_hits["committee_id"].str.replace("_", " ").str.replace("-", " ").str.title()
        # Updated date formatting to short month
        agenda_hits["Meeting Date"] = agenda_hits["meeting_date"].apply(lambda d: d.strftime("%-d %b %Y") if pd.notnull(d) else "")

        # Load original agenda metadata to recover fields like item_title
        with jsonlines.open("data/metadata/agendas.jsonl", "r") as reader:
            agenda_meta = pd.DataFrame(reader)

        # Join on agenda_id, include item_title, item_text, and pdf_urls
        agenda_hits = agenda_hits.merge(agenda_meta[["agenda_id", "item_title", "item_text", "pdf_urls"]], left_on="chunk_id", right_on="agenda_id", how="left")
        # Deduplicate by chunk_id after merging metadata
        agenda_hits = agenda_hits.drop_duplicates(subset="chunk_id")
        # Populate correct date format for agenda items
        agenda_hits["meeting_dt"] = pd.to_datetime(agenda_hits["meeting_date"], unit="ms", errors="coerce")
        agenda_hits["meeting_str"] = agenda_hits["meeting_dt"].dt.strftime("%b %Y")

        # Load meetings.jsonl
        with jsonlines.open("data/metadata/meetings.jsonl", "r") as reader:
            meetings = pd.DataFrame(reader)

        # Merge web_meeting_code into agenda_hits
        agenda_hits = agenda_hits.merge(meetings[["meeting_id", "web_meeting_code"]], on="meeting_id", how="left")

        # Update Meeting Date to be a hyperlink if web_meeting_code is available
        agenda_hits["Meeting Date"] = agenda_hits.apply(
            lambda row: f'<a href="https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row["web_meeting_code"]}" target="_blank">{row["Meeting Date"]}</a>'
            if pd.notnull(row["web_meeting_code"]) and pd.notnull(row["Meeting Date"]) else row["Meeting Date"],
            axis=1
        )

        # Load PDF metadata for display names
        with jsonlines.open("data/metadata/documents.jsonl", "r") as reader:
            documents = pd.DataFrame(reader)
        with jsonlines.open("data/pdf_metadata/scraped_pdf_metadata.jsonl", "r") as reader:
            scraped_meta = pd.DataFrame(reader)
        with jsonlines.open("data/pdf_summaries/summaries.jsonl", "r") as reader:
            summaries = pd.DataFrame(reader)
        pdf_merged = documents.merge(scraped_meta, on="doc_id", how="left")
        pdf_merged = pdf_merged.merge(summaries, on="doc_id", how="left")
        url_to_title = pdf_merged.set_index("url")["item_title"].to_dict()

        # Replace tooltip logic with combined cell content: bold title, full text, PDF links
        def format_agenda_item(title, text, urls):
            clean_text = text.replace("\n\n", "<br><br>").replace("\n", " ")
            html = f"<strong>{title}</strong><br><br>{clean_text}"
            if isinstance(urls, list):
                seen_urls = set()
                for url in urls:
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    doc_info = pdf_merged[pdf_merged["url"] == url]
                    # New label logic per instructions
                    if not doc_info.empty:
                        display = doc_info["display_title"].dropna().values[0] if "display_title" in doc_info and not doc_info["display_title"].dropna().empty else ""
                        filename = doc_info["source_filename"].dropna().values[0] if "source_filename" in doc_info and not doc_info["source_filename"].dropna().empty else ""
                        label = f"{display} ({filename})".strip() if display and filename else display or filename or "View PDF"
                    else:
                        label = "View PDF"
                    html += f'<br><a href="{url}" target="_blank">{label}</a>'
            return html

        agenda_hits["Agenda Item"] = [
            format_agenda_item(
                row["item_title"],
                row["item_text"],
                row.get("pdf_urls", [])
            )
            for _, row in agenda_hits.iterrows()
        ]

        st.write("### Previously Discussed:")
        display_df = agenda_hits[["Meeting Date", "Committee", "Agenda Item"]]
        st.markdown(display_df.head(max_results).to_html(escape=False, index=False), unsafe_allow_html=True)

with tabs[1]:
    new_query = st.text_input(
        "What are you looking for in council records?",
        value=query,
        placeholder="What is the latest council position on 20mph zones?",
        key="pdf_query"
    )
    if new_query != st.session_state["shared_query"]:
        st.session_state["shared_query"] = new_query
        query = new_query
    import jsonlines

    # Use preloaded pdf_merged and meetings data
    # Ensure web_meeting_code is present in pdf_merged, merge if missing
    if "web_meeting_code" not in pdf_merged.columns:
        pdf_merged = pdf_merged.merge(meetings[["meeting_id", "web_meeting_code"]], on="meeting_id", how="left")
    # Create a new column for meeting URL
    pdf_merged["meeting_url"] = pdf_merged["web_meeting_code"].apply(
        lambda mid: f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={mid}" if pd.notnull(mid) else None
    )

    import faiss
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Load summary metadata and FAISS index
    with jsonlines.open("data/embeddings/pdf_summaries/metadata_pdf_summaries.jsonl", "r") as reader:
        summary_meta = pd.DataFrame(reader)
    faiss_index = faiss.read_index("data/embeddings/pdf_summaries/pdf_summary_index.faiss")

    # Embed query and search (only if query is non-empty)
    if query and query.strip():
        query_vector = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding
        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        D, I = faiss_index.search(query_vector, int(max_docs_faiss))
        summary_hits = summary_meta.iloc[I[0]].copy()
        summary_hits["score"] = D[0]
        summary_hits = summary_hits.sort_values("score")
    else:
        summary_hits = summary_meta.head(0).copy()
        summary_hits["score"] = []

    # Guard: suppress table if query is empty
    if not query.strip():
        st.stop()

    # Merge scores into pdf_merged
    filtered_pdf_hits = pdf_merged[pdf_merged["doc_id"].isin(summary_hits["doc_id"])]
    filtered_pdf_hits = filtered_pdf_hits.merge(summary_hits[["doc_id", "score"]], on="doc_id", how="left")
    filtered_pdf_hits = filtered_pdf_hits.sort_values("score")

    # Apply committee filter
    if selected_committee != "All":
        filtered_pdf_hits = filtered_pdf_hits[filtered_pdf_hits["committee_name"] == selected_committee]

    # Apply sorting based on sidebar selection
    if sort_order == "Relevance":
        filtered_pdf_hits = filtered_pdf_hits.sort_values("score")
    elif sort_order == "Date (newest first)":
        filtered_pdf_hits = filtered_pdf_hits.sort_values("meeting_date", ascending=False)
    elif sort_order == "Date (oldest first)":
        filtered_pdf_hits = filtered_pdf_hits.sort_values("meeting_date", ascending=True)
    elif sort_order == "Committee":
        filtered_pdf_hits = filtered_pdf_hits.sort_values("committee_id")

    # Rebuild display table
    filtered_pdf_hits["Meeting Date"] = pd.to_datetime(filtered_pdf_hits["meeting_date"], unit="ms", errors="coerce").dt.strftime("%-d %b %Y")
    filtered_pdf_hits["Meeting Date"] = filtered_pdf_hits.apply(
        lambda row: f'<a href="{row["meeting_url"]}" target="_blank">{row["Meeting Date"]}</a>'
        if pd.notnull(row["meeting_url"]) and pd.notnull(row["Meeting Date"]) else row["Meeting Date"],
        axis=1
    )
    filtered_pdf_hits["Document"] = filtered_pdf_hits.apply(
        lambda row: (
            f'<a href="{row["url"]}" target="_blank"><strong>{row["display_title"]}</strong></a><br>{row["summary"]}'
            if pd.notnull(row["url"]) and pd.notnull(row["display_title"])
            else f'<strong>{row["display_title"]}</strong><br>{row["summary"]}' if pd.notnull(row["display_title"])
            else row["summary"]
        ),
        axis=1
    )
    filtered_pdf_hits["doc_category"] = filtered_pdf_hits["doc_category"].apply(
        lambda val: val.upper() if str(val).lower() in {"prod", "eqia"} else str(val).title()
    )
    pdf_display = filtered_pdf_hits[[
        "Meeting Date",
        "committee_name",
        "doc_category",
        "Document"
    ]].rename(columns={
        "committee_name": "Committee",
        "doc_category": "Type"
    })
    st.write("### The Most Relevant Documents:")
    styled_html = """
<style>
table td:nth-child(1) {
    min-width: 140px;
    white-space: nowrap;
}
</style>
""" + pdf_display.head(max_results).to_html(escape=False, index=False)
    st.markdown(styled_html, unsafe_allow_html=True)


# --- People Tab (tabs[2]) ---
with tabs[2]:
    new_query = st.text_input(
        "What are you looking for in council records?",
        value=st.session_state["shared_query"],
        placeholder="What is the latest council position on 20mph zones?",
        key="people_query"
    )
    if new_query != st.session_state["shared_query"]:
        st.session_state["shared_query"] = new_query
        query = new_query

    st.write("Coming soon: People search results will appear here.")

with tabs[3]:
    new_query = st.text_input(
        "Ask a question about the most relevant documents:",
        value=st.session_state["shared_query"],
        placeholder="What has the council said recently about road maintenance?",
        key="ai_query"
    )
    if new_query != st.session_state["shared_query"]:
        st.session_state["shared_query"] = new_query
        query = new_query

    # Always render and assign new_query, regardless of query state
    question = new_query
    st.sidebar.markdown("### AI Summary Settings")
    top_k = st.sidebar.slider("Number of summaries to send to GPT", min_value=1, max_value=20, value=5)
    context_window = st.sidebar.slider("Adjacent summaries to include", min_value=0, max_value=3, value=1)
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

                def build_user_prompt(query, context_text):
                    return f"""Answer the following question using only the information in the provided context.

Question:
{query}

Relevant Documents:
{context_text}

Answer:"""

                system_prompt = '''
You are a Council Intelligence Analyst. Your job is to explain the Council’s latest thinking on a topic using real documents.

Instructions:
1. Compare multiple documents (agenda items and summaries) from different committees and years.
2. Identify what has changed over time.
3. Cite each source explicitly.
4. If sources conflict, highlight that.

If the same idea appears many times, say: “This is consistent across several documents (e.g., [2024 Cabinet], [2023 Council])…”

If only one strong source is found, say: “Only one detailed agenda item was found, from [Committee, Year]…”

Do not speculate. Be clear about uncertainty or missing details.
'''

                query_vector = client.embeddings.create(input=[question], model="text-embedding-3-small").data[0].embedding
                query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)

                # Load both indexes and metadata
                with jsonlines.open("data/embeddings/pdf_summaries/metadata_pdf_summaries.jsonl", "r") as reader:
                    summaries_df = pd.DataFrame(reader)
                summary_index = faiss.read_index("data/embeddings/pdf_summaries/pdf_summary_index.faiss")
                summary_D, summary_I = summary_index.search(query_vector, 100)

                with jsonlines.open("data/embeddings/agendas/metadata_agenda.jsonl", "r") as reader:
                    agenda_df = pd.DataFrame(reader)
                agenda_index = faiss.read_index("data/embeddings/agendas/agenda_index.faiss")
                agenda_D, agenda_I = agenda_index.search(query_vector, 100)

                summary_hits = summaries_df.iloc[summary_I[0]].copy()
                summary_hits["score"] = summary_D[0]
                summary_hits["source_type"] = "pdf"

                agenda_hits = agenda_df.iloc[agenda_I[0]].copy()
                agenda_hits["score"] = agenda_D[0]
                agenda_hits["source_type"] = "agenda"

                # Always send 4 agenda items and 6 summaries
                agenda_hits = agenda_hits.sort_values("score").drop_duplicates(subset=["chunk_id"]).head(4)
                summary_hits = summary_hits.sort_values("score").drop_duplicates(subset=["doc_id"]).head(6)

                combined = pd.concat([agenda_hits, summary_hits], ignore_index=True)

                # Merge with document metadata for PDF summaries
                with jsonlines.open("data/metadata/documents.jsonl", "r") as reader:
                    documents = pd.DataFrame(reader)

                # Merge PDF summaries to get display_title, committee_name, meeting_date, url
                pdf_combined = combined[combined["source_type"] == "pdf"]
                if not pdf_combined.empty:
                    pdf_combined = pdf_combined.merge(documents, on="doc_id", how="left")

                # For agenda, get agenda metadata for item_title/text
                with jsonlines.open("data/metadata/agendas.jsonl", "r") as reader:
                    agenda_meta = pd.DataFrame(reader)
                agenda_combined = combined[combined["source_type"] == "agenda"]
                if not agenda_combined.empty:
                    agenda_combined = agenda_combined.merge(agenda_meta[["agenda_id", "item_title", "item_text"]], left_on="chunk_id", right_on="agenda_id", how="left")
                    # Load meetings.jsonl to extract web_meeting_code
                    with jsonlines.open("data/metadata/meetings.jsonl", "r") as reader:
                        meetings = pd.DataFrame(reader)
                    agenda_combined = agenda_combined.merge(meetings[["meeting_id", "web_meeting_code"]], on="meeting_id", how="left")

                # Recombine for context building
                all_combined = pd.concat([pdf_combined, agenda_combined], ignore_index=True, sort=False)
                all_combined = all_combined.sort_values("score")

                # Build GPT context
                context = ""
                for _, row in all_combined.iterrows():
                    if row["source_type"] == "pdf":
                        title = row.get("display_title", "Untitled")
                        raw_date = row.get("meeting_date", None)
                        meeting_str = "N/A"
                        try:
                            if isinstance(raw_date, (float, int)) and not pd.isnull(raw_date):
                                meeting_dt = pd.to_datetime(int(raw_date), unit="ms", errors="coerce")
                                meeting_str = meeting_dt.strftime("%-d %b %Y") if pd.notnull(meeting_dt) else "N/A"
                        except Exception:
                            meeting_str = str(raw_date)
                        source_note = f"{row.get('committee_name', 'Unknown Committee')}, {meeting_str}"
                        heading = f"PDF Summary: {title} ({source_note})\n{row.get('text', '')}\n"
                        context += heading + "\n---\n\n"
                    elif row["source_type"] == "agenda":
                        title = row.get("item_title", "Agenda Item")
                        text = row.get("item_text", "")
                        raw_date = row.get("meeting_date", None)
                        meeting_str = "N/A"
                        try:
                            if isinstance(raw_date, (float, int)) and not pd.isnull(raw_date):
                                meeting_dt = pd.to_datetime(int(raw_date), unit="ms", errors="coerce")
                                meeting_str = meeting_dt.strftime("%-d %b %Y") if pd.notnull(meeting_dt) else "N/A"
                        except Exception:
                            meeting_str = str(raw_date)
                        source_note = f"{row.get('committee_id', 'Unknown Committee')}, {meeting_str}"
                        meeting_link = f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row['web_meeting_code']}" if pd.notnull(row.get("web_meeting_code")) else None
                        heading = f"Agenda Item: {title} ({source_note})\n{text}\n"
                        if meeting_link:
                            heading += f"\n[View full meeting]({meeting_link})"
                        context += heading + "\n---\n\n"

                prompt = build_user_prompt(question, context)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
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
                    pdf_links["meeting_str"] = pdf_links["meeting_date"].apply(
                        lambda d: pd.to_datetime(int(d), unit="ms", errors="coerce").strftime("%b %Y") if pd.notnull(d) and isinstance(d, (int, float)) else ""
                    )
                    agenda_links = all_combined[all_combined["source_type"] == "agenda"].head(4).copy()
                    agenda_links["meeting_str"] = agenda_links["meeting_date"].apply(
                        lambda d: pd.to_datetime(int(d), unit="ms", errors="coerce").strftime("%b %Y") if pd.notnull(d) and isinstance(d, (int, float)) else ""
                    )
                    for _, row in pd.concat([agenda_links, pdf_links]).iterrows():
                        url = None
                        title = ""
                        label = ""
                        if row["source_type"] == "pdf" and pd.notnull(row.get("url")):
                            url = row["url"]
                            title = row.get("display_title", "PDF Document")
                            meeting_str = row.get("meeting_str", "")
                            label = f"{title} ({meeting_str})" if meeting_str else title
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