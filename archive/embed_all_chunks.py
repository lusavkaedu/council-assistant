from openai import OpenAI as OpenAIClient

def get_openai_embeddings(texts: list[str], model="text-embedding-3-small", api_key=None) -> list[list[float]]:
    client = OpenAIClient(api_key=api_key)
    response = client.embeddings.create(
        model=model,
        input=texts
    )
    return [item.embedding for item in response.data]
import os
import json
from pathlib import Path
from tqdm import tqdm
import time
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

# === Step 2: Build and Save FAISS Index (Verified Persistence) ===
faiss_index = faiss.IndexFlatL2(Settings.embed_model.dimensions or 1536)
vector_store = FaissVectorStore(faiss_index=faiss_index)

# Initialize storage with explicit docstore/index_store
storage_context = StorageContext.from_defaults(
    docstore=SimpleDocumentStore(),
    index_store=SimpleIndexStore(),
    vector_store=vector_store,
    persist_dir=str(output_dir)
)

# Verify directory exists
output_dir.mkdir(parents=True, exist_ok=True)
print(f"📁 Output directory verified at: {output_dir.absolute()}")

# Batch processing with verification
required_persistence_files = {
    'docstore.json',
    'graph_store.json',
    'index_store.json',
    'vector_store.json'
}

for i in tqdm(range(0, len(all_nodes), batch_size)):
    batch = all_nodes[i:i + batch_size]
    
    # Validate batch (your existing checks)
    valid_nodes = [n for n in batch if validate_node(n)]  # Implement your validation
    
    if not valid_nodes:
        continue

    # Process batch
    try:
        # Create temporary index with current storage context
        VectorStoreIndex(valid_nodes, storage_context=storage_context)
        
        # Verify files were created
        persisted_files = set(os.listdir(output_dir))
        if not required_persistence_files.issubset(persisted_files):
            print(f"⚠️ Missing files after batch {i//batch_size + 1}")
            print(f"Expected: {required_persistence_files}")
            print(f"Found: {persisted_files}")
            raise RuntimeError("Persistence failed")
            
    except Exception as e:
        print(f"🚨 Critical error in batch {i//batch_size + 1}: {str(e)}")
        print("Attempting to save progress...")
        storage_context.persist()
        sys.exit(1)

# Final verification
print("\n🔍 Verifying final persistence...")
storage_context.persist()
persisted_files = set(os.listdir(output_dir))

if required_persistence_files.issubset(persisted_files):
    print("✅ All persistence files created successfully:")
    for f in required_persistence_files:
        print(f" - {f} ({os.path.getsize(output_dir/f)} bytes)")
else:
    missing = required_persistence_files - persisted_files
    raise RuntimeError(f"❌ Missing critical files: {missing}")

print(f"\n💾 Index fully persisted at: {output_dir.absolute()}")