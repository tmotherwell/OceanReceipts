import os
from pathlib import Path
import shutil

def main(receiptPaths, receiptStorageRoot):
    """Move receipt files to folders organized by year extracted from filename.
    
    Args:
        receiptPaths: Dictionary mapping JSON output paths to receipt input filepaths.
        receiptStorageRoot: Root directory path where year folders will be created.
    """
    storage_root = Path(receiptStorageRoot)
    storage_root.mkdir(parents=True, exist_ok=True)
    
    for json_path, receipt_path in receiptPaths.items():
        receipt_file = Path(receipt_path)
        
        if not receipt_file.exists():
            print(f"Warning: Receipt file not found: {receipt_path}")
            continue
        
        # Extract year from filename (first 4 characters, assuming YYYY-MM-DD_merchant format)
        filename = receipt_file.name
        if len(filename) >= 4 and filename[:4].isdigit():
            year = filename[:4]
        else:
            print(f"Warning: Could not extract year from filename: {filename}")
            continue
        
        # Create year folder if it doesn't exist
        year_folder = storage_root / year
        year_folder.mkdir(parents=True, exist_ok=True)
        
        # Move file to year folder
        destination = year_folder / filename
        try:
            shutil.move(str(receipt_file), str(destination))
            print(f"Moved {filename} to {year_folder}")
        except Exception as e:
            print(f"Error moving {filename}: {e}")

