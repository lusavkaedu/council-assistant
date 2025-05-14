import shutil
from openai import OpenAI as OpenAIClient
import os
import json
from pathlib import Path
from tqdm import tqdm
import time
import datetime
import sys
import psutil  # For memory monitoring
import getpass
from tenacity import retry, stop_after_attempt, wait_exponential

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

import faiss

def get_openai_embeddings(texts: list[str], model="text-embedding-3-small", api_key=None) -> list[list[float]]:
    client = OpenAIClient(api_key=api_key)
    response = client.embeddings.create(
        model=model,
        input=texts
    )
    return [item.embedding for item in response.data]

def validate_node(node: TextNode) -> bool:
    """Your custom validation logic"""
    text = node.get_content()
    return bool(text and isinstance(text, str) and text.strip() and len(text) < 15000)

def verify_persistence(output_dir: Path):
    """Verify all required files exist and are non-empty"""
    required_files = {
        'docstore.json',
        'index_store.json',
        'vector_store.json',
        'graph_store.json'
    }
    results = {}
    for f in required_files:
        path = output_dir / f
        exists = path.exists()
        results[f] = {
            'exists': exists,
            'size': path.stat().st_size if exists else 0
        }
    time.sleep(0.2)  # give FS a moment to flush writes
    return results

def print_persistence_status(status):
    print("🔍 Persistence Verification:")
    for file, info in status.items():
        status = "✅" if info['exists'] and info['size'] > 0 else "❌"
        print(f"{status} {file}: {'Exists' if info['exists'] else 'Missing'}, Size: {info['size']} bytes")

# === CONFIGURATION ===
chunk_dir = Path("data/council_documents")
output_dir = Path("data/embedding_index")
output_dir.mkdir(parents=True, exist_ok=True)
embedding_model = "text-embedding-3-small"
chunk_suffix = "_chunks.json"
batch_size = 300


# === DEBUGGING FLAG ===
test_mode = True  # Set to False for full processing
test_sample_size = 100  # Number of nodes to process in test mode

# === Inject API Key ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or getpass.getpass("🔑 Enter your OpenAI API Key: ")

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

# === Step 2: Robust Index Building ===
print("♻️ Resetting index directory...")
if output_dir.exists():
    shutil.rmtree(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)

# Initialize with DEBUG mode
print("💽 Initializing storage with debug mode...")
storage_context = StorageContext.from_defaults(
    docstore=SimpleDocumentStore(),
    index_store=SimpleIndexStore(),
    vector_store=FaissVectorStore(faiss_index=faiss.IndexFlatL2(1536)),
    persist_dir=str(output_dir)
)

# Process in tiny batches first
test_batch = all_nodes[:10]  # Start with just 10 nodes
print("\n🧪 Running test batch...")
try:
    test_index = VectorStoreIndex(test_batch, storage_context=storage_context)
    storage_context.persist()
    time.sleep(0.5)  # allow FS to complete file writes
    
    status = verify_persistence(output_dir)
    print_persistence_status(status)
    
    if not all(v['exists'] and v['size'] > 0 for v in status.values()):
        raise RuntimeError("Test batch failed to persist properly")
    
    print("✅ Test batch successful! Proceeding with full processing...")
except Exception as e:
    print(f"❌ Test batch failed: {str(e)}")
    print("Possible solutions:")
    print("1. Check disk permissions for {output_dir}")
    print("2. Verify enough disk space (df -h)")
    print("3. Try different persist_dir location")
    sys.exit(1)

# Full processing
start_time = datetime.datetime.now()
print("\n⚙️ Processing full dataset...")
for batch_num, i in enumerate(range(10, len(all_nodes), 100)):  # Start from 10
    batch = all_nodes[i:i + 100]
    
    try:
        # Process batch
        VectorStoreIndex(batch, storage_context=storage_context)
        
        # Verify after each batch
        storage_context.persist()
        status = verify_persistence(output_dir)
        
        if not all(v['exists'] and v['size'] > 0 for v in status.values()):
            raise RuntimeError(f"Persistence failed after batch {batch_num}")
            
        print(f"✅ Batch {batch_num} processed ({len(batch)} nodes)")
        print(f"📦 Current index size: {sum(v['size'] for v in status.values())} bytes")
        
    except Exception as e:
        print(f"🛑 Failed at batch {batch_num}: {str(e)}")
        print("💾 Attempting emergency save...")
        storage_context.persist()
        sys.exit(1)

print("\n🎉 Final verification:")
final_status = verify_persistence(output_dir)
print_persistence_status(final_status)
end_time = datetime.datetime.now()
print(f"\n⏱️ Total time: {end_time - start_time}")
print(f"💾 Index saved to: {output_dir}")