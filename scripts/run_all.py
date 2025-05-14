# scripts/run_all.py

import subprocess
import sys
import os
from datetime import datetime
import argparse

parser = argparse.ArgumentParser(description="Run document pipeline scripts.")
parser.add_argument("--mode", choices=["add_on", "re_set"], required=True, help="Pipeline mode to run: 'add_on' (new files only) or 're_set' (full reset)")
args = parser.parse_args()

LOG_PATH = "logs/run_all.log"
os.makedirs("logs", exist_ok=True)

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

def run_script(path):
    print(f"\n🚀 Running {path}...")
    try:
        env = os.environ.copy()
        env["EMBEDDING_TYPE"] = os.getenv("EMBEDDING_TYPE", "small")
        if os.getenv("RESET_EMBEDDINGS"):
            env["RESET_EMBEDDINGS"] = "true"
        result = subprocess.run([sys.executable, path], check=True, env=env)
        log(f"✅ SUCCESS: {path}")
        print(f"✅ Finished {path}\n")
        manifest_path = "data/processed_register/document_manifest.jsonl"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as mf:
                count = sum(1 for _ in mf)
            summary_log_path = "logs/summary.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(summary_log_path, "a", encoding="utf-8") as sf:
                sf.write(f"[{timestamp}] {path} — manifest lines: {count}\n")
    except subprocess.CalledProcessError as e:
        log(f"❌ FAILURE: {path} exited with code {e.returncode}")
        print(f"❌ Script {path} failed with exit code {e.returncode}.")
        sys.exit(e.returncode)
    except Exception as e:
        log(f"❌ ERROR: {path} raised an exception: {e}")
        print(f"❌ Script {path} raised an unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if args.mode == "re_set":
        scripts = [
            "scripts/2_assign_document_ids.py",
            "scripts/2b_text_deduplication.py",
            "scripts/2c_near_duplicate_detection.py",
            "scripts/3_chunking_master.py",
            "scripts/4_embedding_master.py"
        ]
    elif args.mode == "add_on":
        scripts = [
            "scripts/2_assign_document_ids.py",
            "scripts/2b_text_deduplication.py",
            "scripts/2c_near_duplicate_detection.py",
            "scripts/3_chunking_master.py",
            "scripts/4_embedding_master.py"
        ]
    log("===== Script Run Started =====")
    log(f"Running in mode: {args.mode}")
    for script in scripts:
        run_script(script)
    log("🎉 All scripts completed successfully.")
    print("🎉 All scripts completed successfully.")