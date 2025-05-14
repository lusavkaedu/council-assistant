import sys
import os
import json

def fix_encoding(path):
    encodings_to_try = ['utf-8', 'latin1', 'windows-1252']
    for enc in encodings_to_try:
        try:
            with open(path, 'r', encoding=enc) as f:
                data = json.load(f)
            # If successful, re-save as UTF-8
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Fixed encoding using: {enc}")
            return
        except UnicodeDecodeError:
            print(f"❌ Failed with encoding: {enc}")
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decoding issue (not encoding): {e}")
            return
    print("❌ Unable to fix encoding.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_encoding.py <path_to_json_file>")
    else:
        fix_encoding(sys.argv[1])