import os
from pathlib import Path
import shutil

def get_unique_destination(target_path: Path) -> Path:
    """
    Checks if a file exists at the target destination. If it does, 
    appends an incrementing counter (e.g., filename_1.ext, filename_2.ext) 
    until a free path is found.
    """
    if not target_path.exists():
        return target_path
        
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    counter = 1
    
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1

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
        
        # Determine initial destination path
        initial_destination = year_folder / filename
        
        # Resolve any naming conflicts in the destination folder
        final_destination = get_unique_destination(initial_destination)
        
        # Move file to the unique final destination path
        try:
            shutil.move(str(receipt_file), str(final_destination))
            print(f"Moved {filename} to {final_destination}")
        except Exception as e:
            print(f"Error moving {filename} to {final_destination}: {e}")