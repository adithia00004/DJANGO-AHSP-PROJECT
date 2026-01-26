"""
Analyze PDF structure to find AHSP codes like 2.1.1
Based on User's Jupyter notebook approach.
"""

import pdfplumber
import re
import pandas as pd

PDF_PATH = r"D:/PORTOFOLIO ADIT/DJANGO AHSP PROJECT/AHSP Document/AHSP SNI 2025 Bab 2.pdf"

# User's regex pattern for AHSP codes (2.1.1, 2.1.2.3, etc)
REGEX_AHSP_CODE = re.compile(r"(?:^|\s)(\d+(?:\.\d+)+)\b")

def analyze_pdf():
    print(f"Opening: {PDF_PATH}")
    
    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        # Analyze first 3 pages
        for page_num in range(min(3, len(pdf.pages))):
            page = pdf.pages[page_num]
            print(f"\n{'='*60}")
            print(f"PAGE {page_num + 1}")
            print(f"{'='*60}")
            
            # First, extract raw text to find AHSP codes
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                print(f"\n--- Searching for AHSP codes in text ---")
                for i, line in enumerate(lines[:30]):
                    matches = REGEX_AHSP_CODE.findall(line)
                    if matches:
                        print(f"  Line {i}: {matches} <- '{line[:80]}'")
            
            # Then look at tables
            tables = page.extract_tables()
            print(f"\n--- Tables found: {len(tables)} ---")
            
            for t_idx, table in enumerate(tables):
                print(f"\n=== Table {t_idx + 1} ({len(table)} rows) ===")
                for row_idx, row in enumerate(table[:15]):  # First 15 rows
                    # Search for AHSP codes in this row
                    row_text = " ".join(str(c) if c else "" for c in row)
                    matches = REGEX_AHSP_CODE.findall(row_text)
                    
                    if matches:
                        print(f"  Row {row_idx} [AHSP: {matches}]: {row[:5]}")
                    else:
                        print(f"  Row {row_idx}: {row[:5]}")

if __name__ == "__main__":
    analyze_pdf()
