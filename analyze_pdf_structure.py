import pdfplumber
import sys

pdf_path = r"D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\AHSP Document\AHSP CK 2025.pdf"

print("Starting analysis...", flush=True)

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF Opened. Total Pages: {len(pdf.pages)}", flush=True)
        
        # Check page 10 (arbitrary content page)
        try:
            page = pdf.pages[10]
            print("Extracting text from page 10...", flush=True)
            text = page.extract_text()
            if text:
                print("--- Text Found ---")
                print(text[:200])
            else:
                print("--- No Text Found (Possibly Image/Scan) ---")
                
            print("Extracting tables...", flush=True)
            tables = page.extract_tables()
            if tables:
                print(f"--- Found {len(tables)} Tables ---")
                print(tables[0][:2]) # Print first 2 rows
            else:
                print("--- No Tables Found ---")
                
        except IndexError:
            print("Page 10 does not exist.")
            
except Exception as e:
    print(f"Error: {e}")

print("Done.", flush=True)
