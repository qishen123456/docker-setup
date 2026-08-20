import json
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runtime_migration import import_runtime_bundle

def main():
    parser = argparse.ArgumentParser(description="Local runtime migration importer")
    parser.add_argument("file", help="Path to the smartask_runtime_...json file")
    parser.add_argument("--replace", action="store_true", help="Use replace mode instead of merge")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing JSON configs instead of merge")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found.")
        sys.exit(1)
        
    print(f"Loading {args.file} into memory...")
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            bundle = json.load(f)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        sys.exit(1)
        
    mode = "replace" if args.replace else "merge"
    print(f"Starting import (mode: {mode}, overwrite_configs: {args.overwrite})...")
    
    try:
        res = import_runtime_bundle(
            bundle, 
            mode=mode, 
            overwrite_configs=args.overwrite, 
            dry_run=False, 
            auto_backup=True
        )
        if not res.get("ok"):
            print("Import returned non-ok status!")
            print(res)
            sys.exit(1)
            
        print("\n--- Import Success ---")
        print("Written configs:")
        for wc in res.get("written_configs") or []:
            print(f"  - {wc}")
            
        print("\nImported table rows:")
        for table, count in (res.get("imported_counts") or {}).items():
            if count > 0:
                print(f"  - {table}: {count}")
                
        if res.get("skipped_configs"):
            print("\nSkipped configs:")
            for sc in res.get("skipped_configs"):
                print(f"  - {sc}")
                
        print("\nDone! Please restart the backend container if necessary.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
