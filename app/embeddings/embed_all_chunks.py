import os
import json
from pathlib import Path
from tqdm import tqdm
import time
import openai
import datetime

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.readers.file import PyMuPDFReader

import faiss

# === CONFIGURATION ===
chunk_dir = Path("data/council_documents")
output_dir = Path("data/embedding_index")
output_dir.mkdir(parents=True, exist_ok=True)
embedding_model = "text-embedding-3-small"
chunk_suffix = "_chunks.json"

# === Inject API Key ===
from getpass import getpass
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or getpass("🔑 Enter your OpenAI API Key: ")
openai.api_key = OPENAI_API_KEY

existing_index_path = output_dir / "index_store.json"
if existing_index_path.exists():
    print(f"⚠️ Index already exists at {existing_index_path}, skipping embedding...")
    exit()

# === Set Global LlamaIndex Settings ===
Settings.embed_model = OpenAIEmbedding(model=embedding_model, api_key=OPENAI_API_KEY)
Settings.llm = OpenAI(model="gpt-3.5-turbo", api_key=OPENAI_API_KEY)
Settings.node_parser = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

# === Step 1: Load All Chunked Files ===
chunk_files = list(chunk_dir.rglob(f"*{chunk_suffix}"))
print(f"🔍 Found {len(chunk_files)} chunked files to embed...")

all_nodes = []
for path in tqdm(chunk_files):
    try:
        with open(path, "r") as f:
            chunks = json.load(f)
        for chunk in chunks:
            if "text" not in chunk:
                continue
            metadata = {k: v for k, v in chunk.items() if k != "text"}
            node = TextNode(text=chunk["text"], metadata=metadata)
            all_nodes.append(node)
            if len(all_nodes) % 1000 == 0:
                print(f"📝 Collected {len(all_nodes)} text nodes so far...")
    except Exception as e:
        print(f"⚠️ Skipping malformed chunk file {path}: {e}")

print(f"✅ Prepared {len(all_nodes)} text nodes for indexing")

# === Step 2: Build and Save FAISS Index ===
faiss_index = faiss.IndexFlatL2(Settings.embed_model.dimensions or 1536)
vector_store = FaissVectorStore(faiss_index=faiss_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store, persist_dir=str(output_dir))

total_cost = 0
start_time = datetime.datetime.now()

print("💽 Saving embeddings in batches...")
batch_size = 2000
for i in range(0, len(all_nodes), batch_size):
    batch = all_nodes[i:i+batch_size]
    print(f"📦 Saving batch {i//batch_size + 1} with {len(batch)} nodes...")
    partial_index = VectorStoreIndex(batch, storage_context=storage_context)
    try:
        texts = [node.get_content() for node in batch]
        usage_response = openai.Embedding.create(input=texts, model=embedding_model)
        usage = usage_response.usage if hasattr(usage_response, "usage") else {}
        prompt_tokens = usage.get("prompt_tokens", 0)
        batch_cost = (prompt_tokens / 1000) * 0.0001  # Assuming text-embedding-3-small pricing
        total_cost += batch_cost
        print(f"💸 Batch cost estimate: ${batch_cost:.4f} | Total so far: ${total_cost:.4f}")
    except Exception as e:
        print(f"⚠️ Could not estimate cost: {e}")
    time.sleep(0.5)  # small pause to simulate processing

elapsed = datetime.datetime.now() - start_time
print(f"⏱️ Total time: {elapsed}")
print(f"💰 Final estimated embedding cost: ${total_cost:.4f}")

storage_context.persist()

print(f"💾 Index saved to: {output_dir}")