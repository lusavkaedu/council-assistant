import os
import sys
import time
import argparse
from pathlib import Path
from openai import OpenAI
from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader, LLMPredictor, ServiceContext
from langchain.chat_models import ChatOpenAI

def check_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set. Please set it and try again.")
        sys.exit(1)
    print("✅ OpenAI API key found.")

def embed_documents(input_dir: str, output_dir: str):
    input_path = Path(input_dir).absolute()
    output_path = Path(output_dir).absolute()

    print(f"✅ Input directory: {input_path}")
    print(f"✅ Output directory: {output_path}")

    if not input_path.exists() or not input_path.is_dir():
        print(f"❌ Input directory does not exist or is not a directory: {input_path}")
        sys.exit(1)

    output_path.mkdir(parents=True, exist_ok=True)

    print("✅ Reading documents...")
    documents = SimpleDirectoryReader(str(input_path)).load_data()

    print("✅ Initializing LLM predictor...")
    llm_predictor = LLMPredictor(llm=ChatOpenAI(temperature=0, model_name="gpt-4", max_tokens=512))
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)

    print("✅ Creating vector store index...")
    index = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)

    persist_path = output_path / "index.json"
    index.storage_context.persist(persist_dir=str(output_path))
    print(f"✅ Index persisted to {persist_path}")

def main():
    parser = argparse.ArgumentParser(description="Embed documents using GPTVectorStoreIndex")
    parser.add_argument("--input_dir", type=str, default="data", help="Directory containing input documents")
    parser.add_argument("--output_dir", type=str, default="index", help="Directory to store the index")
    args = parser.parse_args()

    check_api_key()
    start_time = time.time()
    embed_documents(args.input_dir, args.output_dir)
    elapsed = time.time() - start_time
    print(f"✅ Embedding process completed in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()