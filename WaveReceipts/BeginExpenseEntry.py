import ExtractReceiptJSON
import PostReceipts
import MoveReceipts
import sys
from pathlib import Path

def assembleReceipts():
    root = Path(__file__).resolve().parent
    json_output_dir = root / "JSONOutput"
    receipt_input_dir = root / "ReceiptInput"
    
    filePaths = {}
    
    if not json_output_dir.exists():
        return filePaths
    
    # Scan JSONOutput folder for JSON files
    for json_file in json_output_dir.glob("*.json"):
        stem = json_file.stem
        
        # Look for matching file in ReceiptInput with same stem (any extension)
        matching_input = None
        if receipt_input_dir.exists():
            for input_file in receipt_input_dir.iterdir():
                if input_file.stem == stem and input_file.is_file():
                    matching_input = input_file
                    break
        
        # Add to mapping if match found
        if matching_input:
            filePaths[str(json_file)] = str(matching_input)
        else:
            print(f"No matching receipt found for {json_file.name}")

    return filePaths
    
def clearJSONFolder():
    """Delete all .json files from the JSONOutput folder."""
    root = Path(__file__).resolve().parent
    json_output_dir = root / "JSONOutput"
    
    if not json_output_dir.exists():
        return
    
    for json_file in json_output_dir.glob("*.json"):
        json_file.unlink()
        print(f"Deleted {json_file.name}")

def main():
    receiptStorageRoot = Path("C:\\Users\\tmotherwell\\Documents\\Corp Docs\\Receipts")
    while True:
        print("Enter 1 to clear JSON output, scan receipts, and post")
        print("Enter 2 for posting only (if you already have the receipt JSON files).")
        user_input = input("<1 or 2>: ")

        if user_input == "1":
            print("Clearing JSON Output folder")
            clearJSONFolder()

            print ("Running OCR and JSON extraction on Receipts")
            receiptPaths = ExtractReceiptJSON.main()

            print("Posting receipts to Wave")
            PostReceipts.main(receiptPaths)

            print("Moving receipts to long term storage folder")
            MoveReceipts.main(receiptPaths, receiptStorageRoot)

            print("Clearing JSON Output")
            clearJSONFolder()

            print("Done!")
            sys.exit(0)

        elif user_input == "2":
            print("Assembling list of receipt JSON and receipt files")
            receiptPaths = assembleReceipts()
            
            print("Posting receipts to Wave")
            PostReceipts.main(receiptPaths)
            
            print("Moving receipts to long term storage folder")
            MoveReceipts.main(receiptPaths, receiptStorageRoot)

            print("Clearing JSON Output")
            clearJSONFolder()

            print("Done!")
            sys.exit(0)
        else:
            print("Invalid input, please enter 1 or 2")

if __name__ == "__main__":
    main()
        