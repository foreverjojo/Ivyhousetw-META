import glob
import os

# Mapping from "part of filename" to "new filename"
# We match by unique substring to avoid encoding issues in shell
MAPPING = [
    ("Dashboard.py", "pages/01_dashboard.py"),
    ("Report_Generation.py", "pages/02_report_generation.py"),
    ("History_Viewer.py", "pages/03_history_viewer.py"),
    ("AI_Assistant.py", "pages/04_ai_assistant.py"),
]


def rename_files():
    files = glob.glob("pages/*.py")
    print(f"Found {len(files)} files in pages/:")
    for f in files:
        print(f" - {f}")

    for substring, new_name in MAPPING:
        found = False
        for f in files:
            if substring in f:
                print(f"Renaming '{f}' -> '{new_name}'")
                try:
                    os.rename(f, new_name)
                    found = True
                    break  # Assuming 1-to-1 match
                except Exception as e:
                    print(f"Error renaming {f}: {e}")
        if not found:
            print(f"Warning: Could not find file matching '{substring}'")


if __name__ == "__main__":
    rename_files()
