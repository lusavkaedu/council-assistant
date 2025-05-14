import os

PROCESSED_DIR = "data/processed_chunks"

def delete_all_chunks(directory=PROCESSED_DIR):
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith("_chunks.json"):
                path = os.path.join(root, file)
                os.remove(path)
                print(f"🗑️ Deleted: {path}")
                count += 1
    print(f"\n✅ Deleted {count} chunk files from {directory}")

if __name__ == "__main__":
    delete_all_chunks()
