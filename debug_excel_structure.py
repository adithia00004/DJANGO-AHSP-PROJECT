"""
Analyze the converted Excel file structure to understand data issues.
"""

import pandas as pd
import re

EXCEL_PATH = r"D:/PORTOFOLIO ADIT/DJANGO AHSP PROJECT/AHSP Document/AHSP CK.xlsx"

def analyze_excel():
    print(f"Opening: {EXCEL_PATH}")
    
    # Get sheet names
    xl = pd.ExcelFile(EXCEL_PATH)
    print(f"\nSheet names: {xl.sheet_names}")
    
    # Analyze first sheet
    for sheet_name in xl.sheet_names[:2]:  # First 2 sheets
        print(f"\n{'='*70}")
        print(f"SHEET: {sheet_name}")
        print(f"{'='*70}")
        
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)
        print(f"Shape: {df.shape} (rows x cols)")
        
        # Show first 30 rows
        print(f"\n--- First 30 rows ---")
        for idx in range(min(30, len(df))):
            row = df.iloc[idx]
            # Show non-null values
            values = []
            for col_idx, val in enumerate(row):
                if pd.notna(val):
                    val_str = str(val)[:50]  # Truncate long values
                    if len(str(val)) > 50:
                        val_str += "..."
                    values.append(f"[{col_idx}]:{val_str}")
            
            if values:
                print(f"Row {idx}: {' | '.join(values)}")
            else:
                print(f"Row {idx}: (empty)")
        
        # Check for multi-line cells
        print(f"\n--- Cells with newlines (multi-value) ---")
        for idx in range(min(100, len(df))):
            row = df.iloc[idx]
            for col_idx, val in enumerate(row):
                if pd.notna(val) and isinstance(val, str) and '\n' in val:
                    print(f"  Row {idx}, Col {col_idx}: {repr(val[:100])}")
        
        # Check for AHSP codes
        print(f"\n--- Rows with AHSP code pattern ---")
        ahsp_pattern = re.compile(r"(\d+(?:\.\d+)+)")
        for idx in range(min(50, len(df))):
            row = df.iloc[idx]
            row_text = " ".join(str(v) for v in row if pd.notna(v))
            matches = ahsp_pattern.findall(row_text)
            if matches:
                print(f"  Row {idx}: codes={matches[:5]}")

if __name__ == "__main__":
    analyze_excel()
