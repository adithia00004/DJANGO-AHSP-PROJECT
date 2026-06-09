"""
Import Views for AHSP Referensi.

3-Tier Import System:
- Opsi 1: PDF to Excel Conversion
- Opsi 2: Excel Validation (dirty Excel)
- Opsi 3: Clean Excel Import
"""

import os
import uuid
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, FileResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from referensi.models_staging import AHSPImportBatch, AHSPImportStaging
from referensi.permissions import has_referensi_import_access
from referensi.services.ahsp_code import (
    CLASSIFICATION,
    PARENT,
    SUBCLASSIFICATION,
    classify_ahsp_code,
    is_ahsp_code,
    normalize_ahsp_code,
)
from referensi.services.import_repair import (
    ACCEPTED_SEGMENTS,
    coerce_koefisien,
    compute_block_status,
    detect_shifted_numbered_row,
    detect_wrapped_row,
    display_segment,
    is_number_like,
    normalize_segment,
    normalized_row_from_original,
    validate_frontend_payload,
)
from referensi.services.import_schema import (
    dump_workbook as dump_interchange_workbook,
    is_interchange_workbook,
    load_workbook_rows as load_interchange_workbook_rows,
)


def is_admin(user):
    """Backward-compatible gate for import endpoints."""
    return has_referensi_import_access(user)


# =============================================================================
# LANDING PAGE
# =============================================================================

@login_required
@user_passes_test(is_admin)
def import_options(request):
    """
    Landing page with 3 import options.
    """
    return render(request, 'referensi/import_options.html')


# =============================================================================
# OPSI 1: PDF TO EXCEL CONVERSION
# =============================================================================

@login_required
@user_passes_test(is_admin)
def import_pdf_convert(request):
    """
    Opsi 1: PDF to Excel Conversion with Batch Support
    """
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        uploaded_file = request.FILES['pdf_file']
        
        if not uploaded_file:
            messages.error(request, "Tidak ada file yang diupload.")
            return redirect('referensi:import_pdf_convert')
        
        if not uploaded_file.name.lower().endswith('.pdf'):
            messages.error(request, "File harus berformat PDF.")
            return redirect('referensi:import_pdf_convert')
        
        # Save file temporarily
        file_id = str(uuid.uuid4())
        
        # Capture Import Mode (import, validation, source)
        import_mode = request.POST.get('import_mode', 'import')
        request.session[f'import_mode_{file_id}'] = import_mode
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
        os.makedirs(temp_dir, exist_ok=True)
        
        pdf_path = os.path.join(temp_dir, f"{file_id}.pdf")
        
        with open(pdf_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Analyze PDF Page Count
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            
            # BATCH THRESHOLD (50 Pages for Timeout Safety)
            BATCH_SIZE = 50
            
            if total_pages > BATCH_SIZE:
                # File too large, show parts selection
                num_parts = (total_pages + BATCH_SIZE - 1) // BATCH_SIZE
                parts = []
                for i in range(num_parts):
                    start = i * BATCH_SIZE + 1
                    end = min((i + 1) * BATCH_SIZE, total_pages)
                    parts.append({
                        'number': i + 1,
                        'start': start,
                        'end': end,
                        'range': f"{start}-{end}"
                    })
                
                return render(request, 'referensi/import_pdf_parts.html', {
                    'file_id': file_id,
                    'file_name': uploaded_file.name,
                    'total_pages': total_pages,
                    'parts': parts
                })
            
            else:
                # Process normally (small file)
                return _process_pdf_pages(request, file_id, pdf_path, 0, total_pages, mode=import_mode)

        except Exception as e:
            messages.error(request, f"Gagal menganalisa file PDF: {str(e)}")
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            return redirect('referensi:import_options')

    return render(request, 'referensi/import_pdf_convert.html')

@login_required
@user_passes_test(is_admin)
def import_pdf_download_part(request, file_id, part_number):
    """
    Download specific part of a large PDF
    """
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
    pdf_path = os.path.join(temp_dir, f"{file_id}.pdf")
    
    if not os.path.exists(pdf_path):
        messages.error(request, "File expired or not found.")
        return redirect('referensi:import_options')
        
    BATCH_SIZE = 50
    part_number = int(part_number)
    
    # Calculate page range (0-indexed)
    start_page = (part_number - 1) * BATCH_SIZE
    # We need to open PDF to get end_page cap
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
    end_page = min(part_number * BATCH_SIZE, total_pages)
    
    import_mode = request.session.get(f'import_mode_{file_id}', 'import')
    return _process_pdf_pages(request, file_id, pdf_path, start_page, end_page, part_suffix=f"_Part{part_number}", mode=import_mode)


@login_required
@user_passes_test(is_admin)
def import_pdf_download_all(request, file_id):
    """
    Process every part of a large PDF and stream them back as a single ZIP.

    Reuses :func:`_process_pdf_pages` (in ``return_path`` mode) for each batch,
    skipping parts that yield no data, then bundles the resulting xlsx files.
    """
    import io
    import zipfile

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
    pdf_path = os.path.join(temp_dir, f"{file_id}.pdf")

    if not os.path.exists(pdf_path):
        messages.error(request, "File expired or not found.")
        return redirect('referensi:import_options')

    BATCH_SIZE = 50

    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    num_parts = (total_pages + BATCH_SIZE - 1) // BATCH_SIZE
    import_mode = request.session.get(f'import_mode_{file_id}', 'import')

    generated = []  # (part_number, excel_path)
    for part_number in range(1, num_parts + 1):
        start_page = (part_number - 1) * BATCH_SIZE
        end_page = min(part_number * BATCH_SIZE, total_pages)
        excel_path = _process_pdf_pages(
            request, file_id, pdf_path, start_page, end_page,
            part_suffix=f"_Part{part_number}", mode=import_mode, return_path=True
        )
        if excel_path and os.path.exists(excel_path):
            generated.append((part_number, excel_path))

    if not generated:
        messages.warning(request, "Tidak ada data tabel yang berhasil dikonversi dari file ini.")
        return redirect('referensi:import_options')

    # Bundle all generated xlsx files into an in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for part_number, path in generated:
            zf.write(path, arcname=f"AHSP_Part_{part_number}.xlsx")
    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="AHSP_Batch_{file_id}.zip"'
    return response


def _process_pdf_pages(request, file_id, pdf_path, start_page, end_page, part_suffix="", mode='import', return_path=False):
    """
    Helper to process a range of PDF pages and return Excel download.

    When ``return_path`` is True the function returns the generated Excel file
    path on success (or ``None`` on failure / no data) instead of issuing an
    HTTP redirect. This is used by the batch download flow so several parts can
    be bundled into a single ZIP.
    """
    try:
        import pdfplumber
        import pandas as pd
        import re
        
        temp_dir = os.path.dirname(pdf_path)
        
        # Append Mode to filename for clarity
        mode_suffix = ""
        if mode == 'validation':
             mode_suffix = "_Validation"
        elif mode == 'validation_hybrid':
             mode_suffix = "_ValidationHybrid"
        elif mode == 'source':
             mode_suffix = "_Source"
        
        excel_filename = f"{file_id}{mode_suffix}{part_suffix}.xlsx"
        excel_path = os.path.join(settings.MEDIA_ROOT, 'temp_imports', excel_filename)
        # Note: If path exists and we append, we might duplicate. 
        # But we create fresh lists below.
        
        all_rows = []
        table_count = 0
        detected_codes = []  # Track AHSP codes for Summary (Code, Title)
        
        # Regex for AHSP codes - STRICTER pattern to reduce false positives
        # Rules:
        # 1. Must be at START of text (^)
        # 2. Minimum 3 number segments (X.X.X) - allows 3+ segments
        # 3. Optional letter suffix at END only (e.g., 1.1.1.a)
        # 4. No letters in the MIDDLE (e.g., 3.4.1.a.3 is invalid)
        # Pattern: Start ^ + digit + (dot + digit) at least 2 times + optional (.letter) at end
        ahsp_pattern = re.compile(r'^(\d+(?:\.\d+){2,}(?:\.[a-zA-Z])?)(?:\s|$)')
        
        skip_column_keywords = ['harga satuan', 'jumlah harga']
        skip_row_keywords = [
            'd. jumlah', 'e. biaya umum', 'f. harga satuan',
            'jumlah harga tenaga kerja, bahan', 
            'biaya umum dan keuntungan',
            'harga satuan pekerjaan (d+e)'
        ]
        
        with pdfplumber.open(pdf_path) as pdf:
            # Process specific range
            for page_idx in range(start_page, end_page):
                if page_idx >= len(pdf.pages): break
                
                page = pdf.pages[page_idx]
                content_items = []
                
                # A. Extract Tables
                # Strategy Selection based on Mode
                if mode == 'validation_hybrid':
                     # HYBRID / LATTICE MODE: Uses lines to detect cells.
                     # Perfect for wrapped text but requires solid table borders.
                     table_settings = {
                        "vertical_strategy": "lines", 
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 3,
                    }
                else:
                    # TEXT MODE (Standard/Validation/Source): Uses text position
                    table_settings = {
                        "vertical_strategy": "lines", 
                        "horizontal_strategy": "text",
                        "snap_tolerance": 3,
                    }
                
                # Pass settings unpacked
                tables = page.find_tables(table_settings)
                extracted_tables_data = page.extract_tables(table_settings)
                
                if tables:
                    for i, table in enumerate(tables):
                        content_items.append({
                            'type': 'table',
                            'top': table.bbox[1],
                            'bbox': table.bbox,
                            'data': extracted_tables_data[i]
                        })
                
                # B. Extract Text Headers
                words = page.extract_words()
                words.sort(key=lambda x: (x['top'], x['x0']))
                
                current_line = []
                lines = []
                last_top = 0
                
                for word in words:
                    if not current_line:
                        current_line.append(word)
                        last_top = word['top']
                    else:
                        if abs(word['top'] - last_top) < 3:
                            current_line.append(word)
                        else:
                            lines.append(current_line)
                            current_line = [word]
                            last_top = word['top']
                if current_line:
                    lines.append(current_line)
                    
                for line_words in lines:
                    line_text = " ".join([w['text'] for w in line_words])
                    top_pos = min(w['top'] for w in line_words)
                    bottom_pos = max(w['bottom'] for w in line_words)
                    
                    inside_table = False
                    if tables:
                        for t in tables:
                            mid_y = (top_pos + bottom_pos) / 2
                            if t.bbox[1] <= mid_y <= t.bbox[3]:
                                inside_table = True
                                break
                    
                    if not inside_table:
                        # LOGIC UPDATE: Multiline Headers
                        # OLD: if ahsp_pattern.search(line_text): -> Dropped lines without code
                        # NEW: Keep if it has code OR if it looks like title continuation
                        # Since we can't know context easily here, we store candidates 
                        # and filter in the Merge step.
                        
                        # But to avoid grabbing page numbers or noise, we can be slightly strict:
                        # - Must have AHSP code
                        # - OR must be close to a previous valid header (handled in merge step?)
                        # Actually, let's just grab mostly everything that looks like text 
                        # and let the merge logic decide validity?
                        # No, that's risky.
                        
                        # Strategy: Store 'potential_header'
                        content_items.append({
                            'type': 'header_candidate', # Temporary type
                            'top': top_pos,
                            'bottom': bottom_pos,
                            'text': line_text
                        })

                # Sort by vertical position
                content_items.sort(key=lambda x: x['top'])
                
                # Merge split headers
                # Logic: If two headers are close and the second doesn't START with a code, merge them.
                merged_items = []
                for item in content_items:
                    # Item is either 'table' or 'header_candidate'
                    
                    if item['type'] == 'table':
                        merged_items.append(item)
                        continue
                        
                    # Handle header_candidate
                    text = item['text'].strip()
                    is_code_start = ahsp_pattern.match(text)
                    
                    if not merged_items:
                        # First item
                        if is_code_start:
                            item['type'] = 'header' # Promote to header
                            merged_items.append(item)
                        # Else: orphan text at start of page (ignore)
                        continue
                        
                    last_item = merged_items[-1]
                    
                    if last_item['type'] == 'header':
                        # Check distance
                        dist = item['top'] - last_item.get('bottom', last_item['top'])
                        
                        if is_code_start:
                            # New Header
                            item['type'] = 'header'
                            merged_items.append(item)
                        elif dist < 15: # Close enough to be continuation (Title wrap)
                            last_item['text'] += " " + text
                            # Update bottom
                            last_item['bottom'] = item['bottom'] 
                        else:
                            # Too far, probably noise or independent text
                            pass
                    else:
                        # Last item was table
                        if is_code_start:
                             item['type'] = 'header'
                             merged_items.append(item)
                        # Else: orphan text after table (ignore)
                
                # Output items
                # C. Flatten Data (Inject Parent Code)
                current_parent_code = None
                current_segment = None # State Machine for A/B/C
                
                # First pass: identify the first header if any
                for item in merged_items:
                    if item['type'] == 'header':
                        match = ahsp_pattern.search(item['text'])
                        if match:
                            current_parent_code = match.group(1).strip()
                            # Track for Summary with segment checklist
                            # +1 for 1-indexed Excel rows
                            detected_codes.append({
                                'code': current_parent_code,
                                'title': item['text'].strip(),
                                'segments': set(),  # Will be populated during processing
                                'data_row': len(all_rows) + 1  # Row number in Data sheet (1-indexed)
                            })
                        
                        # [RESTORED] Add Header Row to Excel for Hierarchy Context
                        # We place the header text in the first column or separate row
                        all_rows.append([item['text']])
                        
                    elif item['type'] == 'table':
                        # Clean table data
                        raw_data = item['data']
                        if not raw_data: continue
                        
                        # Identify skip columns first (including Ghost Columns)
                        skip_col_indices = set()
                        current_col_map = None # Initialize dynamic column map for this table
                        
                        # 1. Keyword-based Skip (Harga Satuan, dll)
                        if mode == 'import' and raw_data and raw_data[0]:
                            for col_idx, header in enumerate(raw_data[0]):
                                if header:
                                    header_lower = str(header).lower()
                                    if any(keyword in header_lower for keyword in skip_column_keywords):
                                        skip_col_indices.add(col_idx)

                        # 2. Ghost Column Skip (100% Empty Columns)
                        if mode == 'import' and raw_data:
                            num_cols = len(raw_data[0])
                            for col_idx in range(num_cols):
                                # Check if this column is empty across ALL rows
                                is_empty_column = True
                                for row in raw_data:
                                    if col_idx < len(row):
                                        cell_val = row[col_idx]
                                        if cell_val and str(cell_val).strip():
                                            is_empty_column = False
                                            break
                                if is_empty_column:
                                    skip_col_indices.add(col_idx)

                        if mode == 'source':
                            # SOURCE: Direct Dump with Segment Tracking
                            for row in raw_data:
                                # Pure raw dump
                                clean_row = []
                                for cell in row:
                                    # Only strip outer whitespace, keep internal format
                                    val = str(cell).strip() if cell else ''
                                    clean_row.append(val)
                                
                                if not any(clean_row): continue
                                
                                # Track segments for Summary checklist
                                row_text = " ".join(clean_row).lower()
                                detected_segment = None
                                if 'tenaga' in row_text and 'kerja' in row_text:
                                    detected_segment = 'TK'
                                elif 'bahan' in row_text and 'jumlah' not in row_text:
                                    detected_segment = 'BHN'
                                elif 'peralatan' in row_text and 'jumlah' not in row_text:
                                    detected_segment = 'PR'
                                elif 'unit' in row_text and 'kerja' in row_text:
                                    detected_segment = 'UNIT_KERJA'
                                elif 'analisa' in row_text and 'pekerjaan' in row_text:
                                    detected_segment = 'ANALISA'
                                elif 'lain' in row_text:
                                    detected_segment = 'LAINNYA'
                                
                                # Associate segment with current parent code
                                if detected_segment and detected_codes and current_parent_code:
                                    for dc in detected_codes:
                                        if dc['code'] == current_parent_code:
                                            dc['segments'].add(detected_segment)
                                            break
                                
                                # DIRECT APPEND - No Extra Columns
                                all_rows.append(clean_row)
                            continue # Skip State Machine

                        for row in raw_data:
                            # Clean cell values
                            clean_row = []
                            for col_idx, cell in enumerate(row):
                                if col_idx not in skip_col_indices:
                                    val = str(cell).strip() if cell else ''
                                    val = val.replace('\n', ' ').strip()
                                    clean_row.append(val)
                            
                            row_text = " ".join(clean_row).lower()
                            if not any(clean_row): continue

                            # --- SEGMENT STATE MACHINE ---
                            # 1. Detect Entry Triggers
                            # Standard Tables
                            detected_segment = None
                            if 'tenaga' in row_text and 'kerja' in row_text and not 'jumlah' in row_text:
                                current_segment = 'TK'
                                detected_segment = 'TK'
                            elif 'bahan' in row_text and not 'jumlah' in row_text:
                                current_segment = 'BHN'
                                detected_segment = 'BHN'
                            elif 'peralatan' in row_text and not 'jumlah' in row_text:
                                current_segment = 'PR'
                                detected_segment = 'PR'
                            elif 'unit' in row_text and 'kerja' in row_text:
                                detected_segment = 'UNIT_KERJA'
                            elif 'analisa' in row_text and 'pekerjaan' in row_text:
                                detected_segment = 'ANALISA'
                            elif 'lain' in row_text:
                                detected_segment = 'LAINNYA'
                            
                            # Track segment in current code's checklist
                            if detected_segment and detected_codes and current_parent_code:
                                for dc in detected_codes:
                                    if dc['code'] == current_parent_code:
                                        dc['segments'].add(detected_segment)
                                        break

                            # 2. Detect Exit Triggers (Footers)
                            if 'jumlah harga' in row_text:
                                # End of current block?
                                pass

                            # Check for Table End Signal (Specific Only)
                            if 'jumlah' in row_text:
                                # Only stop on specific "Jumlah Harga Peralatan" to avoid early exit on "Total" descriptions
                                if mode == 'import':
                                    if 'peralatan' in row_text: 
                                         current_parent_code = None 
                                    continue 
                            
                            # 3. Dynamic Column Detection
                            is_header_row = False
                            is_total_row = False
                            
                            if 'jumlah harga' in row_text:
                                is_total_row = True

                            # Check if this row looks like a header (contains key column names)
                            # Using 'uraian' AND 'koefisien' as strong indicators of a header row.
                            headers_lower = [str(c).lower() for c in clean_row]
                            if 'uraian' in row_text and ('koefisien' in row_text or 'koef' in row_text) and 'kode' in row_text:
                                # Detected Header Row!
                                is_header_row = True
                                current_segment = None # RESET State: New table block starts here.
                                map_idx = {}
                                for idx, val in enumerate(headers_lower):
                                    v = val.strip()
                                    if 'no' == v or 'no.' == v: map_idx['no'] = idx
                                    elif 'uraian' in v: map_idx['uraian'] = idx
                                    elif 'kode' in v: map_idx['kode'] = idx
                                    elif 'satuan' in v: map_idx['satuan'] = idx
                                    elif 'koef' in v: map_idx['koef'] = idx
                                
                                # Only update if mapped at least 3 cols to be safe
                                if len(map_idx) >= 3:
                                    current_col_map = map_idx
                                
                                # Skip header row only in Import mode
                                if mode == 'import':
                                    continue

                            # Inject Parent Code & Segment
                            if current_parent_code:
                                # Prioritize Structural Labels over ANOMALI
                                if current_segment:
                                    seg_val = current_segment
                                elif is_header_row:
                                    seg_val = "HEADER"
                                elif is_total_row:
                                    seg_val = "TOTAL"
                                else:
                                    seg_val = "ANOMALI"
                                
                                # Reorder columns using map if available
                                # Only for IMPORT mode. For Validation/Source, keep raw columns to show defects.
                                if current_col_map and mode == 'import':
                                     # Standard Output: [No, Uraian, Kode, Satuan, Koefisien]
                                     mapped_row = ['-'] * 5 
                                     
                                     def get_val(key):
                                         if key in current_col_map and len(clean_row) > current_col_map[key]:
                                             return clean_row[current_col_map[key]]
                                         return '-'

                                     mapped_row[0] = get_val('no')
                                     mapped_row[1] = get_val('uraian')
                                     mapped_row[2] = get_val('kode')
                                     mapped_row[3] = get_val('satuan')
                                     mapped_row[4] = get_val('koef')
                                     
                                     final_part = mapped_row
                                else:
                                     # Fallback: Use original cleaning
                                     final_part = clean_row

                                final_row = [current_parent_code, seg_val] + final_part
                                all_rows.append(final_row)
                            else:
                                # If no parent code is active (e.g. text after 'Jumlah' but before new header),
                                # we explicitly SKIP this row to avoid orphans.
                                pass 
                            
                        # Table processed
                        table_count += 1
        
        if all_rows:
            # Create Flat DataFrame directly
            df = pd.DataFrame(all_rows)
            
            # --- FILTER UNWANTED ROWS DURING CONVERSION ---
            def get_row_status(row):
                """Determine if row should be kept and why.
                Returns: (keep: bool, reason: str)
                """
                # Combine all cells into text for searching
                row_text = ' '.join([str(v).strip().lower() for v in row if pd.notna(v) and str(v).strip()])
                
                reasons = [] # Accumulate reasons
                should_discard = False
                
                # --- REDUNDANT & FILTER CHECKS (Priority High) ---
                
                # 1. Skip CATATAN rows (PDF footer)
                if row_text.startswith('catatan') or 'catatan :' in row_text or 'catatan:' in row_text:
                    reasons.append('FILTER: Catatan')
                    should_discard = True
                
                # 2. Skip "Biaya Umum dan Keuntungan" rows
                if 'biaya umum' in row_text and 'keuntungan' in row_text:
                    reasons.append('REDUNDANT: Biaya Umum')
                    should_discard = True
                
                # 3. Skip "Harga Satuan Pekerjaan" rows  
                if 'harga satuan pekerjaan' in row_text:
                    reasons.append('REDUNDANT: Harga Satuan')
                    should_discard = True

                # 4. Skip Specific Headers in Anomaly Segments
                if 'unit pekerjaan' in row_text and '*' in row_text: 
                    reasons.append('FILTER: Unit Pekerjaan')
                    should_discard = True
                
                if 'analisa pekerjaan' in row_text:
                    reasons.append('FILTER: Analisa Pekerjaan')
                    should_discard = True
                
                # 5. Skip "Jumlah Harga" rows (Total lines)
                if 'jumlah harga' in row_text or (row_text.startswith('jumlah') and len(row_text) < 50):
                     reasons.append('REDUNDANT: Jumlah Harga')
                     should_discard = True
                     
                # 6. Detect Table Headers (No, Uraian, Satuan, Koefisien...)
                if 'uraian' in row_text and ('koefisien' in row_text or 'koef' in row_text) and 'kode' in row_text:
                    reasons.append('REDUNDANT: Header')
                    should_discard = True

                # 7. Detect Header Fragments/Wrapped Text (e.g. "Harga", "Jumlah", "(Rp)")
                keywords = {'harga', 'jumlah', '(rp)', 'rupiah', 'satuan'}
                tokens = set(row_text.split())
                if len(tokens) < 10 and (len(tokens.intersection(keywords)) >= 1 or '(rp)' in row_text):
                     if 'harga' in row_text and 'jumlah' in row_text:
                         reasons.append('REDUNDANT: Header Fragment')
                         should_discard = True
                     elif row_text.strip() == '(rp)':
                         reasons.append('REDUNDANT: Header Fragment')
                         should_discard = True
                     elif row_text.strip() == 'satuan' or row_text.strip() == 'satuan (rp)':
                         reasons.append('REDUNDANT: Header Fragment')
                         should_discard = True

                # --- DATA ITEM CHECKS (Priority Low) ---

                # Check for Risky Data (Empty Critical Columns)
                # Only if NOT redundant/filtered and looks like a data item
                # Index: 0=Parent, 1=Segment, 2=No, 3=Uraian, 4=Kode, 5=Satuan, 6=Koef
                if len(row) > 1:
                    seg_val = str(row[1]).strip() if len(row) > 1 else ''
                    uraian = str(row[3]).strip() if len(row) > 3 else ''
                    
                    # 8. Check if Uraian is actually a SEGMENT HEADER
                    uraian_lower = uraian.lower()
                    if uraian_lower in ['tenaga kerja', 'bahan', 'peralatan', 'unit kerja', 'analisa pekerjaan', 'lain-lain']:
                        reasons.append('REDUNDANT: Segment Title')
                        should_discard = True

                    if not uraian or uraian == '-':
                         # No Uraian but HAS data? -> Wrapped Data Row
                         if seg_val in ['TK', 'BHN', 'PR'] and len(row) > 6:
                             satuan = str(row[5]).strip() if len(row) > 5 else ''
                             koef = str(row[6]).strip() if len(row) > 6 else ''
                             if satuan and satuan != '-' or koef and koef != '-':
                                 reasons.append('WARNING: Uraian Kosong (Wrapped Data)')
                                 # Warning doesn't necessarily mean discard, keep it for context?
                                 # But in strict Import it should probably be manual fix.
                                 # For validation, we keep everything anyway.
                    
                    elif seg_val in ['TK', 'BHN', 'PR'] and len(row) > 6:
                        satuan = str(row[5]).strip() if len(row) > 5 else ''
                        koef = str(row[6]).strip() if len(row) > 6 else ''
                        
                        is_satuan_empty = not satuan or satuan == '-'
                        is_koef_empty = not koef or koef == '-'
                        
                # --- FINAL CHECK: Segmen ANOMALI ---
                if len(row) > 1 and str(row[1]).strip() == 'ANOMALI':
                    # If it passed all filters (no strict disconnect), add explanation
                    if not should_discard:
                         reasons.append('ANOMALI: Posisi baris tidak diketahui (Di luar Segmen Standar)')
                
                if reasons:
                    return (not should_discard, " // ".join(reasons))
                
                return (True, 'OK')
            
            # Apply filter and track statistics
            stats = {'total': len(df), 'kept': 0, 'filtered': 0, 'risky': 0, 'would_be_filtered': 0, 'redundant': 0, 'warning': 0}
            rows_with_status = []
            
            # Map for Summary: code -> set of segments with warnings
            warning_map = {} 
            # Map for Summary: code -> set of issues (ANOMALI, RISK)
            table_issues_map = {}
            # Counter for Top 5 Issues
            from collections import Counter
            issue_counter = Counter()
            # Track row counts per code (for Empty Table detection)
            code_row_counts = {}

            for idx, row in df.iterrows():
                keep, reason = get_row_status(row)
                
                # Parse Parent Code (Col 0)
                p_code = str(row[0]).strip() if len(row) > 0 else ''
                
                # Track Active Rows per Code
                if p_code and p_code != 'nan':
                     code_row_counts[p_code] = code_row_counts.get(p_code, 0) + 1
                
                # Track Issues (Global Stats)
                if reason and reason != 'OK' and 'REDUNDANT' not in reason and 'FILTER' not in reason:
                     # Split multiple reasons
                     for sub_reason in reason.split(' // '):
                         issue_counter[sub_reason] += 1

                # Track Issues for Summary Table Recap (Per Table)
                if p_code:
                    if p_code not in table_issues_map:
                        table_issues_map[p_code] = set()
                    
                    if 'ANOMALI' in reason:
                        table_issues_map[p_code].add('ANOMALI')
                    if 'RISK' in reason:
                        table_issues_map[p_code].add('RISK')
                    if 'WARNING' in reason:
                        table_issues_map[p_code].add('WARNING')

                # Track Warnings for Summary Checklist (Segment specific)
                if 'WARNING' in reason or 'RISK' in reason:
                    # Parse Segment (Col 1)
                    if len(row) > 1:
                        seg = str(row[1]).strip()
                        if p_code and seg:
                            if p_code not in warning_map:
                                warning_map[p_code] = set()
                            warning_map[p_code].add(seg)

                if mode == 'source':
                    # Source: Keep ALL, no status column, no filter tracking
                    rows_with_status.append(row.tolist())
                    stats['kept'] += 1
                    # Don't increment 'filtered' - nothing is actually filtered
                    
                elif mode in ['validation', 'validation_hybrid']:
                    # Validation: Keep ALL, add status column, track what WOULD be filtered
                    row_list = row.tolist()
                    row_list.append(reason)  # Add Status column
                    rows_with_status.append(row_list)
                    stats['kept'] += 1
                    
                    # Track statistics
                    if 'REDUNDANT' in reason:
                        stats['redundant'] += 1
                    elif 'WARNING' in reason:
                        stats['warning'] += 1
                    elif not keep:
                         stats['would_be_filtered'] += 1
                         
                    # Track risky for awareness
                    if 'RISK' in reason:
                        stats['risky'] += 1
                    # Don't increment 'filtered' - nothing is actually filtered
                    
                else:
                    # Import: Actually filter
                    if keep:
                        rows_with_status.append(row.tolist())
                        if 'RISK' in reason:
                            stats['risky'] += 1
                        stats['kept'] += 1
                    else:
                        stats['filtered'] += 1
            
            df_export = pd.DataFrame(rows_with_status)
            
            # Log filtering info
            print(f"[PDF Conversion] Mode: {mode} | Total: {stats['total']} | Kept: {stats['kept']} | Filtered: {stats['filtered']} | Risky: {stats['risky']} | Redundant: {stats['redundant']} | Warning: {stats['warning']}")
            
            # Export to Excel with Styling, Summary, and Legend
            try:
                from openpyxl.styles import PatternFill, Font, Alignment
                from openpyxl.utils.dataframe import dataframe_to_rows
                
                # Color definitions
                red_fill = PatternFill(start_color='FF9999', end_color='FF9999', fill_type='solid')      # Filtered/Anomaly
                yellow_fill = PatternFill(start_color='FFFFCC', end_color='FFFFCC', fill_type='solid')  # Risky
                grey_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')    # Would be filtered
                green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')   # OK (Light Green)
                redundant_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid') # Redundant (Very Light Green)
                warning_fill = PatternFill(start_color='FFE699', end_color='FFE699', fill_type='solid') # Warning (Light Orange)
                header_font = Font(bold=True)
                
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # === SHEET 1: Data ===
                    data_sheet_name = 'Data'
                    start_row = 1
                    
                    # Add Legend for Raw Mode (at top of sheet)
                    if mode in ['validation', 'validation_hybrid']:
                        legend_data = [
                            ['[ LEGENDA WARNA ]', '', '', '', '', '', '', ''],
                            ['[MERAH/ABU]', 'Baris ini AKAN DIBUANG di Mode Siap Impor', '', '', '', '', '', ''],
                            ['[KUNING]', 'DATA BERISIKO (Satuan/Koefisien kosong pada Item Pekerjaan)', '', '', '', '', '', ''],
                            ['[ORANYE]', 'WARNING (Uraian Kosong tapi ada Data - Indikasi Wrapped Text)', '', '', '', '', '', ''],
                            ['[HIJAU]', 'Baris Redundant (Header/Total) - Aman diabaikan', '', '', '', '', '', ''],
                            ['[PUTIH]', 'Baris Data Valid', '', '', '', '', '', ''],
                            ['', '', '', '', '', '', '', ''],  # Empty row separator
                        ]
                        legend_df = pd.DataFrame(legend_data)
                        legend_df.to_excel(writer, sheet_name=data_sheet_name, index=False, header=False, startrow=0)
                        start_row = len(legend_data)
                    
                    # Write main data
                    df_export.to_excel(writer, sheet_name=data_sheet_name, index=False, header=False, startrow=start_row)
                    
                    workbook = writer.book
                    worksheet = writer.sheets[data_sheet_name]
                    
                    # Style Legend rows (Validation mode)
                    if mode in ['validation', 'validation_hybrid']:
                        for i in range(1, 7):  # Rows 1-6 are legend
                            for cell in worksheet[i]:
                                cell.font = header_font
                    
                    # Apply styling to data rows based on Status column
                    if mode in ['validation', 'validation_hybrid']:
                        # Status column is the LAST column
                        status_col_idx = len(df_export.columns) - 1 if len(df_export.columns) > 0 else -1
                        
                        for idx, row_data in df_export.iterrows():
                            excel_row_num = idx + start_row + 1  # +1 for Excel 1-indexing
                            
                            if status_col_idx >= 0 and len(row_data) > status_col_idx:
                                status = str(row_data.iloc[status_col_idx])
                                
                                if 'REDUNDANT' in status:
                                    # Redundant rows (Headers, Totals)
                                    for cell in worksheet[excel_row_num]:
                                        cell.fill = redundant_fill
                                elif 'WARNING' in status:
                                    # Warnings (Wrapped data)
                                    for cell in worksheet[excel_row_num]:
                                        cell.fill = warning_fill
                                elif 'FILTER' in status:
                                    # This row would be filtered in Import mode
                                    for cell in worksheet[excel_row_num]:
                                        cell.fill = grey_fill
                                elif 'RISK' in status:
                                    # Risky data
                                    for cell in worksheet[excel_row_num]:
                                        cell.fill = yellow_fill
                            
                            # Also check for ANOMALI segment (column 1)
                            # Only color RED if it's NOT already handled by a specific status override
                            # Specifically, REDUNDANT rows should stay GREEN/Ignoring Anomali label
                            if len(row_data) > 1:
                                seg_val = str(row_data.iloc[1]).strip()
                                if seg_val == 'ANOMALI':
                                    # Check if we should override Anomali red
                                    should_red = True
                                    if status_col_idx >= 0:
                                         status = str(row_data.iloc[status_col_idx])
                                         if 'REDUNDANT' in status or 'FILTER' in status:
                                             should_red = False
                                    
                                    if should_red:
                                        for cell in worksheet[excel_row_num]:
                                            cell.fill = red_fill
                    
                    elif mode == 'import':
                        # Import mode: only highlight ANOMALI rows (red)
                        for idx, row_data in df_export.iterrows():
                            excel_row_num = idx + start_row + 1
                            if len(row_data) > 1:
                                seg_val = str(row_data.iloc[1]).strip()
                                if seg_val == 'ANOMALI':
                                    for cell in worksheet[excel_row_num]:
                                        cell.fill = red_fill
                    
                    # === SHEET 2: Summary (ALL MODES) ===
                    
                    # 1. Calculate Health Metrics
                    all_codes = [item['code'] for item in detected_codes]
                    code_counts_series = Counter(all_codes)
                    duplicate_codes = [code for code, count in code_counts_series.items() if count > 1]
                    
                    empty_tables = []
                    for item in detected_codes:
                        code = item['code']
                        if code_row_counts.get(code, 0) < 2: 
                            empty_tables.append(code)

                    summary_data = [
                        ['RINGKASAN KONVERSI PDF', ''],
                        ['', ''],
                        ['Mode Import', mode.upper()],
                        ['', ''],
                        ['Total Baris Diekstrak', stats['total']],
                        ['Baris Dipertahankan', stats['kept']],
                        ['Baris Difilter/Dibuang', stats['filtered']],
                    ]
                    
                    if mode in ['validation', 'validation_hybrid']:
                        summary_data.append(['Calon Baris Akan Difilter', stats['would_be_filtered']])
                        summary_data.append(['Baris Redundant (Header/Total)', stats['redundant']])
                        
                    summary_data.extend([
                        ['Baris Berisiko (Data Kosong)', stats['risky']],
                        ['Baris Warning (Uraian Kosong)', stats['warning']],
                        ['', ''],
                        ['', ''],
                        ['[ HEALTH CHECK ]', ''],
                        ['Duplikasi Kode AHSP', f"{len(duplicate_codes)} ({', '.join(duplicate_codes[:3])}{'...' if len(duplicate_codes)>3 else ''})"],
                        ['Tabel Kosong (Zombie)', f"{len(empty_tables)}"],
                        ['', ''],
                        ['[ TOP 5 MASALAH VALIDASI ]', ''],
                    ])
                    
                    # Add Top 5 Issues
                    if issue_counter:
                        most_common = issue_counter.most_common(5)
                        for issue, count in most_common:
                            summary_data.append([issue, count])
                    else:
                        summary_data.append(['Tidak ada isu signifikan', '-'])
                    
                    summary_data.extend([
                        ['', ''],
                        ['Total Tabel AHSP Terdeteksi', len(detected_codes)],
                    ])
                    
                    # Add AHSP Code listing (Table of Contents) for Source AND Validation Check mode
                    toc_data_start_row = 0  # Will track where AHSP items start in summary
                    if mode in ['source', 'validation', 'validation_hybrid'] and detected_codes:
                        summary_data.append(['', ''])
                        summary_data.append(['[ DAFTAR ISI AHSP ]', '', '', '', '', '', '', ''])
                        # Header row with segment columns
                        summary_data.append(['Kode', 'Judul', 'TK', 'BHN', 'PR', 'Unit Kerja', 'Analisa', 'Lainnya'])
                        
                        toc_data_start_row = len(summary_data) # Start of data rows (0-indexed in list)
                        
                        for item in detected_codes:
                            code = item['code']
                            segs = item['segments']
                            data_row = item.get('data_row', 1)
                            actual_excel_row = data_row   # Assuming data_row is already inclusive of legend offset? No.
                            # 'data_row' was set as `len(all_rows) + 1`. This is without Legend.
                            # Correct Row = start_row (Legend Size) + data_row
                            target_row = start_row + data_row 

                            # Create Link to Data Sheet
                            link_val = f'=HYPERLINK("#\'Data\'!A{target_row}", "{item["title"]}")'
                            
                            # Helper to format checkmark
                            def get_mark(seg_key):
                                mark = "v" if seg_key in segs else "-"
                                if seg_key in segs and code in warning_map and seg_key in warning_map[code]:
                                    return "(!) v"
                                return mark

                            # Get Code Status
                            issues_list = []
                            # 1. Structural Checks
                            if code in duplicate_codes:
                                issues_list.append("DUPLICATE")
                            if code in empty_tables:
                                issues_list.append("EMPTY/ZOMBIE")
                            # 2. Row Issue Checks
                            if code in table_issues_map and table_issues_map[code]:
                                row_issues = sorted(list(table_issues_map[code]))
                                issues_list.extend(row_issues)
                                
                            status_text = ", ".join(issues_list) if issues_list else "OK"

                            row = [
                                code,
                                link_val,
                                get_mark('TK'),
                                get_mark('BHN'),
                                get_mark('PR'),
                                get_mark('UNIT_KERJA'),
                                get_mark('ANALISA'),
                                get_mark('LAINNYA'),
                                status_text
                            ]
                            summary_data.append(row)
                        
                        # Add classification breakdown
                        # Group by first level (e.g., 4.1, 4.2)
                        classifications = {}
                        for item in detected_codes:
                            parts = item['code'].split('.')
                            if len(parts) >= 2:
                                klasifikasi = f"{parts[0]}.{parts[1]}"
                                if klasifikasi not in classifications:
                                    classifications[klasifikasi] = 0
                                classifications[klasifikasi] += 1
                        
                        if classifications:
                            summary_data.append(['', ''])
                            summary_data.append(['[ RINGKASAN KLASIFIKASI ]', ''])
                            summary_data.append(['Klasifikasi', 'Jumlah AHSP'])
                            for klasifikasi, count in sorted(classifications.items()):
                                summary_data.append([klasifikasi, count])
                    
                    # === FILTER DOCUMENTATION (ALL MODES) ===
                    summary_data.append(['', ''])
                    summary_data.append(['[ FILTER YANG DITERAPKAN ]', ''])
                    summary_data.append(['Filter', 'Deskripsi'])
                    summary_data.append(['FILTER: Catatan', 'Baris yang diawali "Catatan" atau mengandung "Catatan :"'])
                    summary_data.append(['FILTER: Biaya Umum', 'Baris yang mengandung "Biaya Umum dan Keuntungan"'])
                    summary_data.append(['FILTER: Harga Satuan', 'Baris yang mengandung "Harga Satuan Pekerjaan"'])
                    summary_data.append(['FILTER: Unit Pekerjaan', 'Baris header "Unit Pekerjaan *)"'])
                    summary_data.append(['FILTER: Analisa Pekerjaan', 'Baris header "Analisa Pekerjaan"'])
                    summary_data.append(['', ''])
                    summary_data.append(['RISK: Data Kosong', 'Baris dengan Satuan atau Koefisien kosong/"-"'])
                    summary_data.append(['', ''])
                    summary_data.append(['Catatan:', 'Filter hanya aktif di mode "Siap Impor". Mode lain menampilkan semua baris.'])
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False, header=False)
                    
                    # Style Summary sheet
                    summary_ws = writer.sheets['Summary']
                    summary_ws['A1'].font = Font(bold=True, size=14)
                    for row in range(3, 15):
                         summary_ws[f'A{row}'].font = Font(bold=True)
                    
                    # Style TOC Header if exists
                    if toc_data_start_row > 0:
                         toc_header_row_num = toc_data_start_row # Excel Row Number ("Kode, Judul...")
                         # Note: toc_data_start_row is 1-based index of the header row in Excel?
                         # Let's verify: In list it was `len(summary_data)`.
                         # to_excel startrow=0, header=False.
                         # So list index 0 is Excel row 1.
                         # list index N is Excel row N+1.
                         # So `toc_data_start_row` (list index) corresponds to Excel Row `toc_data_start_row + 1`.
                         
                         excel_header_row = toc_data_start_row + 1
                         
                         for col in range(1, 10):
                             summary_ws.cell(row=excel_header_row, column=col).font = header_font
                             
                         # Style Segment Warning Cells (Orange) & Status Column
                         for i, item in enumerate(detected_codes):
                             excel_row = excel_header_row + 1 + i
                             # Columns C to H (3 to 8) are segments
                             for col_idx in range(3, 9): 
                                 cell = summary_ws.cell(row=excel_row, column=col_idx)
                                 if "(!)" in str(cell.value):
                                     cell.fill = warning_fill
                                     cell.font = Font(color="9C5700", bold=True) # Dark Orange Text
                             
                             # Column I (9) is Keterangan
                             cell_status = summary_ws.cell(row=excel_row, column=9)
                             val_status = str(cell_status.value)
                             if 'ANOMALI' in val_status or 'DUPLICATE' in val_status or 'ZOMBIE' in val_status or 'EMPTY' in val_status:
                                 cell_status.fill = red_fill
                                 cell_status.font = Font(bold=True)
                             elif 'RISK' in val_status or 'WARNING' in val_status:
                                 cell_status.fill = warning_fill
                                 cell_status.font = Font(color="9C5700", bold=True)
                             elif val_status == 'OK':
                                 cell_status.fill = green_fill
                                 cell_status.font = Font(color="006100", bold=True)
                    
            except ImportError:
                 # Fallback if openpyxl not installed
                 df_export.to_excel(excel_path, sheet_name='Data', index=False, header=False)
            
            if return_path:
                return excel_path
            return redirect('referensi:import_pdf_download', file_id=f"{file_id}{mode_suffix}{part_suffix}")
        else:
            if return_path:
                return None
            messages.warning(request, "Tidak ditemukan data tabel pada halaman ini.")
            return redirect('referensi:import_options')

    except Exception as e:
        # Clean up if failed
        if 'excel_path' in locals() and os.path.exists(excel_path):
            os.remove(excel_path)
        if return_path:
            return None
        messages.error(request, f"Error processing: {str(e)}")
        return redirect('referensi:import_options')


@login_required
@user_passes_test(is_admin)
def pdf_convert_download(request, file_id):
    """
    Download converted Excel file.
    """
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
    excel_path = os.path.join(temp_dir, f"{file_id}.xlsx")
    
    if os.path.exists(excel_path):
        return FileResponse(
            open(excel_path, 'rb'),
            as_attachment=True,
            filename=f"converted_{file_id}.xlsx"
        )
    else:
        messages.error(request, "File tidak ditemukan.")
        return redirect('referensi:import_pdf_convert')


# =============================================================================
# OPSI 2: EXCEL VALIDATION
# =============================================================================

@login_required
@user_passes_test(is_admin)
def excel_validate_upload(request):
    """
    Opsi 2: Upload one OR MORE Excel files for validation.

    Multiple conversion-output files share the same "Data" sheet layout, so we
    merge their rows into ONE combined workbook and validate it as a single
    report -> a single "Download Data Valid" output. Legend rows of each file are
    skipped downstream by the validator, and differing column widths are handled
    positionally, so mixed-width merges are safe.
    """
    if request.method == 'POST':
        files = request.FILES.getlist('excel_file')

        if not files:
            messages.error(request, "Tidak ada file yang diupload.")
            return redirect('referensi:import_validate')

        invalid = [f.name for f in files if not f.name.lower().endswith(('.xlsx', '.xls'))]
        if invalid:
            messages.error(
                request,
                f"File harus berformat Excel (.xlsx/.xls): {', '.join(invalid[:5])}",
            )
            return redirect('referensi:import_validate')

        import pandas as pd

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
        os.makedirs(temp_dir, exist_ok=True)
        file_id = uuid.uuid4().hex[:12]
        excel_path = os.path.join(temp_dir, f"{file_id}_validate.xlsx")

        try:
            frames = []
            codes_per_file = {}
            for f in files:
                xls = pd.ExcelFile(f)
                # Prefer the "Data" sheet; fall back to the first sheet.
                data_sheet = next(
                    (n for n in xls.sheet_names if n.strip().lower() == 'data'),
                    xls.sheet_names[0],
                )
                df = pd.read_excel(xls, sheet_name=data_sheet, header=None)
                frames.append(df)

                # Collect valid AHSP code tokens (col 0) for cross-file dup warning.
                seen = set()
                if df.shape[1]:
                    for value in df.iloc[:, 0].tolist():
                        token = str(value).split(' ')[0].strip() if value is not None else ''
                        if is_ahsp_code(token):
                            seen.add(normalize_ahsp_code(token))
                codes_per_file[f.name] = seen

            combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                combined.to_excel(writer, sheet_name='Data', index=False, header=False)
        except Exception as e:
            if os.path.exists(excel_path):
                os.remove(excel_path)
            messages.error(request, f"Gagal membaca/menggabungkan file: {e}")
            return redirect('referensi:import_validate')

        if len(files) > 1:
            total_rows = sum(len(fr) for fr in frames)
            messages.info(
                request,
                f"{len(files)} file digabung menjadi satu validasi ({total_rows} baris).",
            )
            from collections import Counter
            counter = Counter()
            for seen in codes_per_file.values():
                for code in seen:
                    counter[code] += 1
            dups = sorted(code for code, n in counter.items() if n > 1)
            if dups:
                preview = ', '.join(dups[:8])
                extra = f" (+{len(dups) - 8} lagi)" if len(dups) > 8 else ""
                messages.warning(
                    request,
                    f"{len(dups)} kode AHSP muncul di lebih dari satu file: {preview}{extra}. "
                    "Pilih mode commit (merge/replace) saat commit untuk menangani duplikat.",
                )

        # Redirect to validation report (single combined file -> single download)
        return redirect('referensi:import_validate_report', file_id=file_id)
    
    return render(request, 'referensi/import_validate.html')


# --- Persisted Edit Mode changes (survive pagination + feed the download) ------

def _validation_edits_path(file_id):
    return os.path.join(settings.MEDIA_ROOT, 'temp_imports', f"{file_id}_edits.json")


def _load_validation_edits(file_id):
    import json
    if not file_id:
        return {}
    path = _validation_edits_path(file_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_validation_edits(file_id, data_rows, hierarchy):
    """Merge a page's Edit Mode rows into the JSON sidecar (by parent code)."""
    import json
    store = _load_validation_edits(file_id)
    titles = {}
    for h in hierarchy or []:
        code = str(h.get('code', '')).strip()
        if code:
            titles[code] = h.get('title', '') or code

    incoming = {}
    for r in data_rows or []:
        parent = str(r.get('parent_code', '')).strip()
        if not parent:
            continue
        incoming.setdefault(parent, []).append({
            'row_id': str(r.get('row_id', '')),
            'segment': r.get('segment', '-'),
            'no': r.get('no', '-'),
            'uraian': r.get('uraian', '-'),
            'kode_ref': r.get('kode_ref', '-'),
            'satuan': r.get('satuan', '-'),
            'koefisien': r.get('koefisien', '-'),
        })

    # Replace each parent present in THIS page's payload (others kept untouched).
    for parent, rows in incoming.items():
        prev_title = store.get(parent, {}).get('title', parent) if isinstance(store.get(parent), dict) else parent
        store[parent] = {'title': titles.get(parent, prev_title), 'rows': rows}

    os.makedirs(os.path.dirname(_validation_edits_path(file_id)), exist_ok=True)
    with open(_validation_edits_path(file_id), 'w', encoding='utf-8') as fh:
        json.dump(store, fh)
    return len(incoming)


def _effective_status(item):
    """Single source of truth for a table's display status (blocked/warning/valid).

    Used by both the initial parse and the edit-replay path so every badge on
    the report page (nav, detail, filter, summary) stays in lock-step instead of
    each spot re-deriving status from divergent fields.
    """
    if item.get('is_blocked'):
        return 'blocked'
    if item.get('table_status') in ('warning', 'error') or item.get('warnings'):
        return 'warning'
    return 'valid'


def _apply_edits_to_results(results, edits):
    """Rebuild table_container rows + status from persisted edits so revisiting a
    page shows the admin's changes."""
    if not edits:
        return
    for idx, item in enumerate(results):
        if item.get('type') != 'table_container':
            continue
        parent = str(item.get('first_col', '')).split(' ')[0].strip()
        info = edits.get(parent)
        if not info:
            continue
        grouped = {'TK': [], 'BHN': [], 'PR': [], 'ANOMALI': [], 'LAIN': []}
        for r in info.get('rows', []):
            seg_raw = str(r.get('segment', '')).strip().upper()
            bucket = 'LAIN' if seg_raw in ('LAIN', 'LAINNYA') else display_segment(r.get('segment'))
            if bucket not in grouped:
                bucket = 'ANOMALI'
            grouped[bucket].append({
                'row': r.get('row_id', ''),
                'original_row': {
                    'col_0': parent, 'col_1': r.get('segment', '-'),
                    'col_2': r.get('no', '-'), 'col_3': r.get('uraian', '-'),
                    'col_4': r.get('kode_ref', '-'), 'col_5': r.get('satuan', '-'),
                    'col_6': r.get('koefisien', '-'),
                },
                'severity': 'valid', 'issues': [],
            })
        item['grouped_rows'] = grouped
        item['table_rows'] = [ri for rows in grouped.values() for ri in rows]
        normalized_rows = [normalized_row_from_original(ri['original_row']) for ri in item['table_rows']]
        item.update(compute_block_status({'rows': normalized_rows}))
        # Koefisien rule: non-numeric coefficient assumed 0 (after block status so
        # the passive warning still fires on the raw edited value).
        for ri in item['table_rows']:
            o = ri.get('original_row', {})
            if (
                normalize_segment(o.get('col_1')) in ACCEPTED_SEGMENTS
                and str(o.get('col_3', '')).strip() not in ('', '-')
                and not is_number_like(o.get('col_6'))
            ):
                o['col_6'] = coerce_koefisien(o.get('col_6'))
        # Recompute table_status + the canonical effective_status from the edited
        # rows so all badges reflect the edit (not stale pre-edit state).
        has_anomali = len(grouped['ANOMALI']) > 0
        item['is_anomaly'] = has_anomali
        item['table_status'] = (
            'error' if has_anomali else ('warning' if item.get('warnings') else 'valid')
        )
        item['effective_status'] = _effective_status(item)
        # Keep the linked parent (nav tree) in sync with the edited table.
        for j in range(idx - 1, -1, -1):
            if results[j].get('type') == 'hierarchy_parent':
                results[j]['child_table_status'] = item['table_status']
                results[j]['child_effective_status'] = item['effective_status']
                results[j]['child_is_anomaly'] = item['is_anomaly']
                results[j]['child_is_blocked'] = item['is_blocked']
                break


@login_required
@user_passes_test(is_admin)
@require_POST
def save_validation_edits(request, file_id):
    """Persist per-page Edit Mode changes so they survive pagination."""
    import json
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    saved = _save_validation_edits(
        file_id, data.get('data_rows', []), data.get('hierarchy', [])
    )
    return JsonResponse({'ok': True, 'saved_parents': saved})


@login_required
@user_passes_test(is_admin)
def excel_validate_report(request, file_id):
    """
    Show validation report for uploaded Excel.
    Enhanced validation based on AHSP document structure.
    """
    import pandas as pd
    import re
    
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
    excel_path = os.path.join(temp_dir, f"{file_id}_validate.xlsx")
    
    if not os.path.exists(excel_path):
        messages.error(request, "File tidak ditemukan.")
        return redirect('referensi:import_validate')
    
    # Create report context
    try:
        results, df_len, counts = _get_validation_results(excel_path)

        # Store validated file path + id in session for export/save-edits.
        request.session['validated_excel_path'] = excel_path
        request.session['validation_file_id'] = file_id

        # Apply any persisted Edit Mode changes so they survive pagination and the
        # report reflects the admin's edits on revisit.
        _apply_edits_to_results(results, _load_validation_edits(file_id))

        # Paginate the rendered entries so big imports stay light in the browser
        # while the admin can still page through EVERYTHING. The DOWNLOAD is never
        # limited by the page: export_from_frontend supplements any non-rendered
        # tables from the server-side validated file (Edit Mode applies per page).
        from django.core.paginator import Paginator

        PER_PAGE = 250
        paginator = Paginator(results, PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page'))
        display_results = list(page_obj.object_list)
        table_results = [item for item in results if item.get('type') == 'table_container']

        # --- Input/output-aware summary stats --------------------------------
        # Surface what actually happened to the uploaded file so the admin can
        # reconcile it: how many physical rows came in, how many became real
        # data, how many are structure, and how many were discarded as noise.
        ahsp_count = len(table_results)
        data_rows_total = sum(len(t.get('table_rows', [])) for t in table_results)
        warning_rows = 0
        danger_rows = 0
        for t in table_results:
            for r in t.get('table_rows', []):
                sev = r.get('severity', 'valid')
                if sev == 'danger':
                    danger_rows += 1
                elif sev == 'warning':
                    warning_rows += 1
        valid_rows = max(0, data_rows_total - warning_rows - danger_rows)

        # Structural rows: AHSP titles, classification/sub-classification folders
        # and table header rows -- present in the file but not item data.
        struct_rows = sum(
            1 for it in results
            if it.get('type') in (
                'hierarchy_class', 'hierarchy_subclass', 'hierarchy_parent', 'header'
            )
        )
        folder_count = sum(
            1 for it in results
            if it.get('type') in ('hierarchy_class', 'hierarchy_subclass')
        )
        # Everything physically in the file that became neither data nor
        # structure: blank rows, segment headers (TENAGA KERJA/BAHAN/PERALATAN),
        # CATATAN, subtotals (Jumlah Harga), legend rows and other PDF noise that
        # the parser intentionally skips.
        discarded_rows = max(0, df_len - data_rows_total - struct_rows)

        context = {
            'file_id': file_id,
            'results': display_results,
            'page_obj': page_obj,
            'is_paginated': paginator.num_pages > 1,
            'per_page': PER_PAGE,
            'total_rows': df_len,
            'total_entries': len(results),
            # New, more relevant summary
            'ahsp_count': ahsp_count,
            'data_rows_total': data_rows_total,
            'valid_rows': valid_rows,
            'warning_rows': warning_rows,
            'danger_rows': danger_rows,
            'struct_rows': struct_rows,
            'folder_count': folder_count,
            'discarded_rows': discarded_rows,
            # Kept for the blocked-tables alert / Data Valid messaging
            'valid_count': counts['valid'],
            'warning_count': counts['warning'],
            'info_count': counts['info'],
            'danger_count': counts['danger'],
            'exportable_table_count': sum(1 for item in table_results if item.get('can_export')),
            'blocked_table_count': sum(1 for item in table_results if item.get('is_blocked')),
        }
        return render(request, 'referensi/import_validate_report.html', context)
        
    except Exception as e:
        messages.error(request, f"Error membaca Excel: {str(e)}")
        return redirect('referensi:import_validate')


@login_required
@user_passes_test(is_admin)
def excel_validate_download(request, file_id):
    """
    Download validation report as Excel with annotations.
    """
    import pandas as pd
    
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
    excel_path = os.path.join(temp_dir, f"{file_id}_validate.xlsx")
    
    if not os.path.exists(excel_path):
        messages.error(request, "File tidak ditemukan.")
        return redirect('referensi:import_validate')

    try:
        results, _, _ = _get_validation_results(excel_path)
        # Reflect any persisted Edit Mode changes so the annotated download
        # matches what the admin sees/exports elsewhere.
        _apply_edits_to_results(results, _load_validation_edits(file_id))

        # Reconstruct DataFrame with Notes
        rows_data = []
        for r in results:
            # We want original row content + Note
            # Note: We need to preserve original content better in the helper if possible, 
            # currently helper stores 'preview'.
            # Let's simple re-read or adjust helper to store raw data?
            # For efficiency, let's just use the preview or re-read. 
            # Actually, to be accurate, we should carry the row data. 
            pass 
        
        # Simpler approach: Re-read df inside helper and return rich objects?
        # Let's adjust helper below to be robust.
        
        # RE-IMPLEMENTING HELPER & DOWNLOAD LOGIC FULLY BELOW
        pass
    except Exception:
        pass

    # ... implementation continues via helper ...
    return _generate_validation_excel(excel_path, file_id)

def _get_validation_results(excel_path):
    """
    Helper to validate Excel rows.
    """
    import pandas as pd
    import re
    
    ahsp_block_pattern = re.compile(r'(?:^|\s)(\d+(?:\.\d+){2,})\b')
    item_code_pattern = re.compile(r'^[A-Za-z]{1,6}\.?\d')
    header_keywords = ['no', 'uraian', 'kode', 'satuan', 'koefisien', 'harga']
    
    results = []
    counts = {'valid': 0, 'warning': 0, 'info': 0, 'danger': 0}
    
    display_df = pd.read_excel(excel_path, header=None)
    
    # AHSP code parsing/classification is delegated to the single source of
    # truth in referensi.services.ahsp_code (supports letter suffixes such as
    # 2.2.1.1.5.a and rejects malformed codes consistently across all flows).

    for idx, row in display_df.iterrows():
        # Get raw columns reliably (pandas Series)
        # Col 0: Parent Code / Header Text
        # Col 1: Segment (A/B/C/UK/LL) - New Format
        
        raw_col_0 = str(row[0]).strip() if pd.notna(row[0]) else ""
        raw_col_1 = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""
        
        # Compact values for text searching
        row_values = [str(v).strip() for v in row if pd.notna(v) and str(v).strip()]
        if not row_values: continue
        row_text = " ".join(row_values)
        
        issues = []
        severity = "valid"
        row_type = "data"
        
        first_col = raw_col_0 # Use specific column 0 checking
        first_token = first_col.split(' ')[0] if first_col else ""
        code_class = classify_ahsp_code(first_token)

        # 1. Check HIERARCHY HEADERS (classification handled by ahsp_code helper,
        # which understands letter suffixes such as 2.2.1.1.5.a).
        if code_class == CLASSIFICATION:
             issues.append(f"Hierarchy: Klasifikasi ({first_token})")
             severity = "info" # Blue
             row_type = "hierarchy_class"

        elif code_class in (SUBCLASSIFICATION, PARENT):
             # 3-5 numeric segments (+optional letter suffix). A code is an AHSP
             # PARENT when it BEARS DATA (segment rows); segment-count alone does
             # NOT decide -- AHSP 2026 uses 3-segment codes as real work items
             # (e.g. 3.2.1 with TK/BHN/PR). A bare 3-segment header with no data
             # is reclassified back to a sub-klasifikasi folder in a later pass
             # (see "Reclassify bare 3-segment parents"). See SPEC S? / data taxonomy.
             # Header Block vs Data Row?
             is_data_row = False
             if len(row_values) >= 3: is_data_row = True
             if raw_col_1 in ['A', 'B', 'C', 'UK', 'LL', 'TK', 'BHN', 'PR']: is_data_row = True

             if not is_data_row:
                 # It's a Parent Header (Title Row)
                 issues.append(f"Hierarchy: AHSP Parent ({first_token})")
                 severity = "success"
                 row_type = "hierarchy_parent"
             else:
                 # It's a DATA ROW
                 # Check Segment Anomaly
                 if raw_col_1 == 'UK':
                     issues.append("Tabel Anomali: Unit Kerja (Cek Manual)")
                     severity = "warning" # Yellow per User Request
                     row_type = "anomaly_uk"
                 elif raw_col_1 == 'LL':
                     issues.append("Tabel Anomali: Lain-lain (Format Non-Standar)")
                     severity = "warning"
                     row_type = "anomaly_ll"

                 # Check for explicit text if Segment Col is missing (Old Format Fallback)
                 elif 'unit kerja' in row_text.lower():
                     issues.append("Refactorable: Segmen Unit Kerja")
                     severity = "info" # Keep info for fallback
                     row_type = "two_segment"
                 elif 'lain-lain' in row_text.lower():
                     issues.append("Refactorable: Segmen Lain-lain")
                     severity = "info"
                     row_type = "two_segment"

                 # Parent Code Integrity: col_0 of a data row must itself be a
                 # valid AHSP code (previously referenced an undefined regex).
                 if not is_ahsp_code(first_col):
                        if 'jumlah' in row_text.lower():
                             issues.append("Subtotal Row")
                             severity = "info"
                             row_type = "subtotal"
                        else:
                             issues.append("CRITICAL: Invalid Parent Code")
                             severity = "danger"
                             row_type = "invalid_parent"

        # 2. Check Metadata/Header Keywords
        elif sum(1 for kw in header_keywords if kw in row_text.lower()) >= 3:
            issues.append("Table Header Row")
            severity = "info"
            row_type = "header"
            
        else:
            # Fallback for lines that don't match codes
            if 'jumlah' in row_text.lower():
                 severity = "info"
                 row_type = "subtotal"
            else:
                 # Unknown text
                 issues.append("Unknown Row Format")
                 severity = "warning"
                 row_type = "unknown"

        # Calculate Tree indent (UI Level)
        # Heuristic: Count dots in the first token
        ui_level = 0
        is_folder = False
        
        # Safe dot count
        try:
            dots = first_token.count('.')
        except:
            dots = 0
            
        if row_type.startswith('hierarchy_'):
            ui_level = max(0, dots - 1) * 20
            is_folder = True
        elif row_type == 'header':
            # Table Header e.g. "No Uraian..."
            # Should be indented inside parent?
            ui_level = 60 
            is_folder = False
        else:
            # ALL Data variants (data, anomaly_uk, subtotal, invalid_parent, etc.)
            # Must be deeper than Parent (Level 40)
            ui_level = 60 
            is_folder = False
        
        # Clean row data: Convert nan/None to "-" and create dict for template
        import math
        def clean_value(val):
            if val is None:
                return "-"
            if isinstance(val, float) and math.isnan(val):
                return "-"
            s = str(val).strip()
            if s.lower() in ['nan', 'none', '']:
                return "-"
            return s
        
        row_list = row.tolist()
        clean_row = {
            'col_0': clean_value(row_list[0]) if len(row_list) > 0 else '-',
            'col_1': clean_value(row_list[1]) if len(row_list) > 1 else '-',  # Segment
            'col_2': clean_value(row_list[2]) if len(row_list) > 2 else '-',  # No
            'col_3': clean_value(row_list[3]) if len(row_list) > 3 else '-',  # Uraian
            'col_4': clean_value(row_list[4]) if len(row_list) > 4 else '-',  # Kode
            'col_5': clean_value(row_list[5]) if len(row_list) > 5 else '-',  # Satuan
            'col_6': clean_value(row_list[6]) if len(row_list) > 6 else '-',  # Koefisien
            'row_id': str(idx + 1),
        }

        nonempty_cells = [clean_value(v) for v in row_list if clean_value(v) != '-']
        validation_status_markers = (
            'OK',
            'REDUNDANT',
            'ANOMALI',
            'RISK',
            'WARNING',
            'DUPLICATE',
            'ZOMBIE',
            'EMPTY',
        )

        def is_validation_status(value):
            value_upper = str(value).strip().upper()
            return any(value_upper.startswith(marker) for marker in validation_status_markers)

        # Skip header rows from generated validation/source workbooks.
        if clean_row['col_1'].strip().upper() == 'HEADER':
            continue

        # Wide fixed-column conversion output (the standard PDF->Excel layout) has
        # Status/Harga columns BEYOND Koefisien (col_6), so the last non-empty cell
        # sits at a high index. For those rows the positional clean_row is already
        # correct and MUST NOT be re-packed: re-packing nonempty cells mis-shifts
        # rows whose interior Kode column (col_4) is legitimately empty -- very
        # common for Bahan/Peralatan items without a reference code (see
        # docs/SPEC_VALIDASI_DATA_AHSP.md, S1). Compact re-pack is only for genuinely
        # narrow workbooks where Status immediately follows the payload.
        last_nonempty_idx = max(
            (i for i, v in enumerate(row_list) if clean_value(v) != '-'),
            default=-1,
        )
        is_fixed_format = last_nonempty_idx >= 7
        segment_value = clean_row['col_1'].strip().upper()

        def normalize_wide_fixed_data_row():
            """Recover rows where PDF extraction spread payload across wide columns.

            Some AHSP PDFs place Kode/Satuan/Koefisien at columns like 6/9/12
            while item descriptions without a code land in the old Kode column.
            This maps the rightmost unit/coefficient pair back to the canonical
            report shape: No, Uraian, Kode, Satuan, Koefisien.
            """
            if not is_fixed_format or segment_value not in {'A', 'B', 'C', 'TK', 'BHN', 'PR'}:
                return None
            if row_type != 'data':
                return None

            payload = []
            for pos, value in enumerate(row_list[2:], start=2):
                clean = clean_value(value)
                if clean == '-' or is_validation_status(clean):
                    continue
                payload.append((pos, clean))

            if not payload:
                return None

            koef_pos = None
            koef_value = ''
            for pos, value in reversed(payload):
                if pos >= 5 and is_number_like(value):
                    koef_pos = pos
                    koef_value = value
                    break
            if koef_pos is None:
                return None

            before_koef = [(pos, value) for pos, value in payload if pos < koef_pos]
            if not before_koef:
                return None

            satuan_pos, satuan_value = before_koef[-1]
            text_items = [(pos, value) for pos, value in before_koef[:-1]]
            if not text_items:
                return None

            no_value = clean_row['col_2'] if clean_row['col_2'] != '-' else '-'
            if text_items and text_items[0][0] == 2:
                no_value = text_items[0][1]
                text_items = text_items[1:]

            code_idx = None
            for item_idx, (_pos, value) in enumerate(text_items):
                if item_code_pattern.match(str(value).strip()):
                    code_idx = item_idx
                    break

            if code_idx is not None:
                kode_value = text_items[code_idx][1]
                uraian_parts = [value for _pos, value in text_items[:code_idx]]
                if not uraian_parts and code_idx > 0:
                    uraian_parts = [text_items[0][1]]
                uraian_value = " ".join(uraian_parts).strip() if uraian_parts else text_items[0][1]
            elif len(text_items) >= 2:
                uraian_value = " ".join(value for _pos, value in text_items)
                kode_value = '-'
            else:
                uraian_value = text_items[0][1]
                kode_value = '-'

            if not uraian_value or not satuan_value or not koef_value:
                return None

            return {
                'col_0': clean_row['col_0'],
                'col_1': segment_value,
                'col_2': no_value,
                'col_3': uraian_value,
                'col_4': kode_value,
                'col_5': satuan_value,
                'col_6': koef_value,
                'row_id': str(idx + 1),
            }

        wide_normalized = normalize_wide_fixed_data_row()
        if wide_normalized:
            clean_row = wide_normalized

        # Generated validation/source workbooks can be compact:
        # [Parent, Segment, Uraian, Kode/Satuan, Satuan/Koef, Koef/Status, Status]
        # Normalize them to the display/export shape expected by this report:
        # [Parent, Segment, No, Uraian, Kode, Satuan, Koefisien].
        segment_value = clean_row['col_1'].strip().upper()
        if (
            not is_fixed_format
            and len(nonempty_cells) >= 4
            and segment_value in {'A', 'B', 'C', 'TK', 'BHN', 'PR', 'ANOMALI'}
            and is_validation_status(nonempty_cells[-1])
        ):
            source_status = str(nonempty_cells[-1]).strip()
            payload = nonempty_cells[2:-1]
            segment_title_map = {
                'A': ('TK', 'tenaga kerja'),
                'TK': ('TK', 'tenaga kerja'),
                'B': ('BHN', 'bahan'),
                'BHN': ('BHN', 'bahan'),
                'C': ('PR', 'peralatan'),
                'PR': ('PR', 'peralatan'),
            }
            expected = segment_title_map.get(segment_value)

            if expected and len(payload) >= 2 and str(payload[1]).strip().lower() == expected[1]:
                results.append({
                    'row': idx + 1,
                    'type': 'segment_header_marker',
                    'segment_code': expected[0],
                    'hidden': True
                })
                continue

            if len(payload) >= 5:
                normalized = {
                    'col_0': clean_row['col_0'],
                    'col_1': segment_value,
                    'col_2': payload[0],
                    'col_3': payload[1],
                    'col_4': payload[2],
                    'col_5': payload[3],
                    'col_6': payload[4],
                    'row_id': str(idx + 1),
                }
            elif len(payload) == 4:
                normalized = {
                    'col_0': clean_row['col_0'],
                    'col_1': segment_value,
                    'col_2': '-',
                    'col_3': payload[0],
                    'col_4': payload[1],
                    'col_5': payload[2],
                    'col_6': payload[3],
                    'row_id': str(idx + 1),
                }
            elif len(payload) == 3:
                normalized = {
                    'col_0': clean_row['col_0'],
                    'col_1': segment_value,
                    'col_2': '-',
                    'col_3': payload[0],
                    'col_4': '-',
                    'col_5': payload[1],
                    'col_6': payload[2],
                    'row_id': str(idx + 1),
                }
            else:
                normalized = None

            if normalized:
                clean_row = normalized
                if 'WARNING: Uraian Kosong' in source_status:
                    issues.append('WARNING: Uraian Kosong (Wrapped Data)')
                    if severity not in {'danger'}:
                        severity = 'warning'

        is_wrapped, _repair_candidate = detect_wrapped_row(clean_row)
        if is_wrapped and 'WARNING: Uraian Kosong (Wrapped Data)' not in issues:
            issues.append('WARNING: Uraian Kosong (Wrapped Data)')
            if severity not in {'danger'}:
                severity = 'warning'

        is_shifted, _shifted_candidate = detect_shifted_numbered_row(clean_row)
        if is_shifted and 'WARNING: Kolom Bergeser (No/Uraian/Kode)' not in issues:
            issues.append('WARNING: Kolom Bergeser (No/Uraian/Kode)')
            if severity not in {'danger'}:
                severity = 'warning'

        # --- SKIP UNWANTED ROWS ---
        row_text_lower = row_text.lower()

        # 0. Skip legend/metadata rows from generated workbooks (e.g.
        # "[ LEGENDA WARNA ]", "[MERAH/ABU] ...") so they do not leak into a
        # phantom "Unknown" ANOMALI table (see SPEC S5).
        if clean_row['col_0'].startswith('['):
            continue

        # 0b. Skip the column-number guide row that AHSP PDF tables print right
        # under the header -- "(1) (2) (3) (4) (5)" numbering each column. Its
        # payload cells (No/Uraian/Kode/Satuan/Koefisien) are just a consecutive
        # integer sequence 1,2,3,4,5.. which is NEVER real item data, yet it
        # otherwise leaks in as a phantom ANOMALI row and wrongly BLOCKS an
        # otherwise-valid AHSP (e.g. 2.6.2.1 / 2.6.2.2). Discard it as noise.
        enum_seq = [
            clean_row[f'col_{i}'] for i in range(2, 7)
            if clean_row[f'col_{i}'] not in ('', '-')
        ]
        if (
            len(enum_seq) >= 4
            and all(c.isdigit() for c in enum_seq)
            and [int(c) for c in enum_seq] == list(range(1, len(enum_seq) + 1))
        ):
            continue

        # 1. Track and skip segment header rows (A/B/C TENAGA KERJA, BAHAN, etc.)
        # BUT record that we SAW this segment header for anomaly detection
        segment_header_map = {
            'tenaga kerja': 'TK', 
            'bahan': 'BHN', 
            'peralatan': 'PR', 
            # UK and LL removed from explicit mapping, will be skipped or treated as text
        }
        uraian_lower = clean_row['col_3'].lower()
        is_segment_header = False
        for header_text, seg_code in segment_header_map.items():
            if header_text in uraian_lower and clean_row['col_4'] == '-':
                is_segment_header = True
                # Record this as a seen segment header (for anomaly check later)
                results.append({
                    'row': idx + 1,
                    'type': 'segment_header_marker',
                    'segment_code': seg_code,
                    'hidden': True  # Won't be displayed, just tracked
                })
                break
        if is_segment_header:
            continue
        
        # 2. Skip CATATAN rows (PDF footer)
        if row_text_lower.startswith('catatan') or 'catatan :' in row_text_lower or 'catatan:' in row_text_lower:
            continue
        
        # 3. Skip "Biaya Umum dan Keuntungan" rows
        if 'biaya umum' in row_text_lower and 'keuntungan' in row_text_lower:
            continue
        
        # 4. Skip "Harga Satuan Pekerjaan" rows  
        if 'harga satuan pekerjaan' in row_text_lower:
            continue
        
        # 5. Skip "Jumlah Harga" summary rows (but keep subtotals with segment)
        if 'jumlah harga' in row_text_lower and clean_row['col_1'] == '-':
            continue
        
        results.append({
            'row': idx + 1,
            'original_row': clean_row, 
            'preview': row_text[:100] + '...',
            'first_col': first_col,
            'issues': issues,
            'severity': severity, 
            'type': row_type,
            'ui_level': ui_level,
            'is_folder': is_folder
        })
    
    # --- POST-PROCESSING: GROUP DATA INTO TABLES ---
    grouped_results = []
    current_table_node = None
    last_parent_index = None  # Track last hierarchy_parent for linking
    last_parent_code = 'Unknown' # Track last parent code for table container

    def get_segment_key(row_item):
        # Extract Segment from original row (col_1 = Segment column)
        # Source/clean Excel can use either document labels (A/B/C) or UI labels
        # (TK/BHN/PR). Normalize both forms before grouping for display/export.
        try:
            return display_segment(row_item['original_row']['col_1'])
        except:
            return 'ANOMALI'
    
    def calculate_table_status(table_rows):
        """Compute worst severity across all rows in a table."""
        has_danger = any(r.get('severity') == 'danger' for r in table_rows)
        has_warning = any(r.get('severity') == 'warning' for r in table_rows)
        # Check for ANOMALI rows
        has_anomali = any(get_segment_key(r) == 'ANOMALI' for r in table_rows)
        if has_anomali: return 'error' # Treat ANOMALI as error? or warning? User said "decide manually", so Warning/Error. Let's say Warning/Info? 
                                       # Actually user said "label as anomaly". Usually this means red/danger.
        
        if has_danger: return 'error'
        if has_warning: return 'warning'
        return 'valid'

    # Track segment headers seen per table
    current_segment_headers = set()
    
    for item in results:
        if item.get('type') == 'segment_header_marker':
            # Track this segment header was seen
            current_segment_headers.add(item['segment_code'])
            continue  # Don't add to grouped_results
            
        if item['type'].startswith('hierarchy_') or item['type'] == 'header':
            # Attach collected segment headers to the current table before reset
            if current_table_node:
                current_table_node['seen_segment_headers'] = current_segment_headers.copy()
            
            # Track the last parent for linking
            if item['type'] == 'hierarchy_parent':
                last_parent_index = len(grouped_results)
                # Capture clean code (first token)
                raw_col = item.get('first_col', '-')
                last_parent_code = raw_col.split(' ')[0].strip()
                current_segment_headers = set()  # Reset for new AHSP
            grouped_results.append(item)
            current_table_node = None
        else:
            # Data Row
            if current_table_node:
                seg = get_segment_key(item)
                current_table_node['grouped_rows'][seg].append(item)
                current_table_node['table_rows'].append(item)
            else:
                # Start new table container
                current_table_node = {
                    'type': 'table_container',
                    'row': item['row'],
                    'first_col': last_parent_code, # Use captured parent code
                    'ui_level': 60,
                    'is_folder': False,
                    'table_rows': [item],
                    'grouped_rows': {
                        'TK': [], 'BHN': [], 'PR': [], 'LAIN': [], 'ANOMALI': []
                    },
                    'seen_segment_headers': current_segment_headers.copy(),
                    'preview': 'Grouped Data',
                    'severity': 'valid',
                    'issues': [],
                    'table_status': 'valid',
                    'is_anomaly': False,
                    'anomaly_reasons': [],
                    'block_status': 'valid',
                    'blocked_reasons': [],
                    'repair_candidates': [],
                    'can_export': True,
                }
                seg = get_segment_key(item)
                current_table_node['grouped_rows'][seg].append(item)
                grouped_results.append(current_table_node)
    
    # Finalize last table's headers
    if current_table_node:
        current_table_node['seen_segment_headers'] = current_segment_headers.copy()

    def merge_wrapped_continuation_rows(table_node):
        """Merge PDF wrapped continuation rows into the previous valid item."""
        merged_rows = []
        for row_item in table_node.get('table_rows', []):
            orig = row_item.get('original_row', {})
            seg = get_segment_key(row_item)
            continuation_text = ''
            if (
                seg in {'TK', 'BHN', 'PR', 'LAIN'}
                and orig.get('col_2', '-') in {'', '-'}
                and orig.get('col_5', '-') in {'', '-'}
                and orig.get('col_6', '-') in {'', '-'}
            ):
                continuation_text = (
                    orig.get('col_3') if orig.get('col_3', '-') not in {'', '-'}
                    else orig.get('col_4') if orig.get('col_4', '-') not in {'', '-'}
                    else ''
                )

            if continuation_text:
                previous = next(
                    (
                        existing for existing in reversed(merged_rows)
                        if get_segment_key(existing) == seg
                        and existing.get('original_row', {}).get('col_3', '-') not in {'', '-'}
                        and existing.get('original_row', {}).get('col_5', '-') not in {'', '-'}
                        and existing.get('original_row', {}).get('col_6', '-') not in {'', '-'}
                    ),
                    None,
                )
                if previous:
                    prev_orig = previous['original_row']
                    prev_orig['col_3'] = f"{prev_orig.get('col_3', '').strip()} {continuation_text.strip()}".strip()
                    continue

            merged_rows.append(row_item)

        table_node['table_rows'] = merged_rows
        table_node['grouped_rows'] = {'TK': [], 'BHN': [], 'PR': [], 'LAIN': [], 'ANOMALI': []}
        for row_item in merged_rows:
            table_node['grouped_rows'][get_segment_key(row_item)].append(row_item)
    
    # Second pass: Calculate table_status, segment completeness, and link to parent
    for i, item in enumerate(grouped_results):
        if item['type'] == 'table_container':
            merge_wrapped_continuation_rows(item)
            # Calculate base status from row severities
            item['table_status'] = calculate_table_status(item['table_rows'])
            
            # --- SEGMENT STRUCTURE CHECK ---
            # Missing standard segments (TK/BHN/PR) is a PASSIVE warning only and
            # is computed downstream by compute_block_status; it must NOT mark the
            # table as anomaly/blocked because some AHSP items legitimately have no
            # Bahan/Peralatan. Only genuine ANOMALI (unknown) data is a real anomaly.
            has_data_anomali = len(item['grouped_rows']['ANOMALI']) > 0
            if has_data_anomali:
                item['is_anomaly'] = True
                item['anomaly_reasons'].append(
                    f"Terdapat {len(item['grouped_rows']['ANOMALI'])} baris ANOMALI (Segmen tidak dikenal)"
                )
                if item['table_status'] == 'valid':
                    item['table_status'] = 'warning'

            normalized_rows = [
                {
                    **normalized_row_from_original(row_item.get('original_row', {})),
                    "issues": row_item.get("issues", []),
                }
                for row_item in item.get('table_rows', [])
            ]
            block_status = compute_block_status({
                'rows': normalized_rows,
                'is_anomaly': item.get('is_anomaly', False),
                'anomaly_reasons': item.get('anomaly_reasons', []),
                'table_status': item.get('table_status'),
            })
            item.update(block_status)

            # Koefisien rule: a detail item's non-numeric coefficient is assumed
            # to be 0. Done AFTER compute_block_status so the passive warning is
            # still raised on the raw value; here we coerce the value shown in the
            # report and carried into every export (DB staging already coerces).
            for row_item in item.get('table_rows', []):
                orig = row_item.get('original_row', {})
                if (
                    normalize_segment(orig.get('col_1')) in ACCEPTED_SEGMENTS
                    and str(orig.get('col_3', '')).strip() not in ('', '-')
                    and not is_number_like(orig.get('col_6'))
                ):
                    orig['col_6'] = coerce_koefisien(orig.get('col_6'))

            # Passive warnings (missing Bahan/Peralatan) downgrade to 'warning'
            # but keep the table exportable (is_blocked stays False).
            if (item['is_blocked'] or item.get('warnings')) and item['table_status'] == 'valid':
                item['table_status'] = 'warning'

            # SINGLE SOURCE OF TRUTH for every status badge on the page (nav,
            # detail, filter, dynamic JS): one tri-state (blocked/warning/valid)
            # that collapses the previously-divergent table_status/is_blocked/
            # is_anomaly fields. See _effective_status().
            item['effective_status'] = _effective_status(item)

            # Link to preceding hierarchy_parent
            for j in range(i - 1, -1, -1):
                if grouped_results[j]['type'] == 'hierarchy_parent':
                    grouped_results[j]['child_table_status'] = item['table_status']
                    grouped_results[j]['child_effective_status'] = item['effective_status']
                    grouped_results[j]['child_is_anomaly'] = item['is_anomaly']
                    grouped_results[j]['child_is_blocked'] = item['is_blocked']
                    break

    # Recompute summary counters from the final rendered rows after all
    # normalizers (wide-column remap, wrapped-continuation merge, anomaly
    # grouping) have run. Pre-merge warning rows may no longer exist visually.
    final_counts = {'valid': 0, 'warning': 0, 'info': 0, 'danger': 0}
    for item in grouped_results:
        if item.get('type') == 'table_container':
            for row_item in item.get('table_rows', []):
                sev = row_item.get('severity', 'valid')
                final_counts[sev] = final_counts.get(sev, 0) + 1
        elif item.get('type') != 'segment_header_marker':
            sev = item.get('severity')
            if sev in final_counts or sev == 'success':
                final_counts[sev] = final_counts.get(sev, 0) + 1
    counts = final_counts

    # Reclassify bare 3-segment parents that ended up with NO data table back to
    # sub-klasifikasi folders (e.g. "3.1.1 ATAP GENTENG" headers). 3-segment codes
    # that DO carry data (e.g. 3.2.1 with TK/BHN/PR) keep their data table and stay
    # AHSP parents. (child_table_status is only set when a data table linked to it.)
    for item in grouped_results:
        if (
            item.get('type') == 'hierarchy_parent'
            and 'child_table_status' not in item
            and classify_ahsp_code(str(item.get('first_col', '')).split(' ')[0]) == SUBCLASSIFICATION
        ):
            item['type'] = 'hierarchy_subclass'

    return grouped_results, len(display_df), counts


def _generate_validation_excel(excel_path, file_id):
    """
    Generate Excel file with [VALIDATION_NOTES] column.
    """
    import pandas as pd
    from django.http import FileResponse
    
    results, _, _ = _get_validation_results(excel_path)
    
    data_rows = []
    
    for r in results:
        # Get original values as list
        vals = r['original_row'].tolist()
        # Add Note
        note = "; ".join(r['issues']) if r['severity'] != 'valid' else 'OK'
        vals.append(note)
        data_rows.append(vals)
        
    # Create new DF
    new_df = pd.DataFrame(data_rows)
    # Rename last col
    new_cols = list(range(len(new_df.columns) - 1)) + ['[VALIDATION_NOTES]']
    new_df.columns = new_cols
    
    output_path = excel_path.replace('.xlsx', '_annotated.xlsx')
    new_df.to_excel(output_path, index=False, header=False)
    
    return FileResponse(open(output_path, 'rb'), as_attachment=True, filename=f"Validation_Report_{file_id}.xlsx")


# =============================================================================
# OPSI 3: CLEAN EXCEL IMPORT
# =============================================================================

def _bounded_text(value, *, field_name, max_length, context):
    text = "" if value is None else str(value).strip()
    if len(text) > max_length:
        raise ValueError(
            f"Kolom {field_name} terlalu panjang ({len(text)} karakter, maksimal {max_length}) "
            f"pada {context}. Kemungkinan ada kolom Excel yang bergeser/wrapped; perbaiki file atau jalankan validasi/repair dulu."
        )
    return text


def _create_staging_row(**kwargs):
    context = (
        f"parent={kwargs.get('parent_ahsp_code') or kwargs.get('kode_item') or '-'}, "
        f"segmen={kwargs.get('segment_type') or '-'}"
    )
    for field_name, max_length in (
        ("file_name", 255),
        ("sumber", 100),
        ("parent_ahsp_code", 50),
        ("segment_type", 20),
        ("kode_item", 50),
        ("satuan_item", 50),
    ):
        if field_name in kwargs:
            kwargs[field_name] = _bounded_text(
                kwargs.get(field_name),
                field_name=field_name,
                max_length=max_length,
                context=context,
            )
    return AHSPImportStaging.objects.create(**kwargs)


def _stage_rincian_from_export(user, file_name, xls, data_sheet, sheet_names, sumber, batch=None):
    """Stage rincian from a canonical 'Data Valid'/'Data Anomali' export workbook.

    Reads the data sheet by COLUMN NAME (robust to the extra 'No' column that the
    export adds) and the 'Daftar Isi' sheet for parent titles. Codes are normalized
    on both sides so each HEADING (title) links to its data rows at commit time.
    """
    import pandas as pd
    from referensi.services.ahsp_code import normalize_ahsp_code

    def cell(row, col):
        if col is None:
            return ''
        val = row.get(col, '')
        return '' if pd.isna(val) else str(val).strip()

    # 1. Titles from "Daftar Isi" -> HEADING rows (linked to data by parent code).
    toc_sheet = next((n for n in sheet_names if n.strip().lower() == 'daftar isi'), None)
    if toc_sheet:
        toc = pd.read_excel(xls, sheet_name=toc_sheet)
        tcols = {str(c).strip().lower(): c for c in toc.columns}
        c_code, c_title = tcols.get('kode ahsp'), tcols.get('judul pekerjaan')
        for _, row in toc.iterrows():
            code = normalize_ahsp_code(cell(row, c_code))
            if not code:
                continue
            title = cell(row, c_title)
            _create_staging_row(
                user=user, batch=batch, file_name=file_name, sumber=sumber,
                segment_type='HEADING', kode_item=code,
                uraian_item=title or code, parent_ahsp_code=None, is_valid=True,
            )

    # 2. Data rows mapped by column NAME (handles the extra 'No' column correctly).
    data = pd.read_excel(xls, sheet_name=data_sheet)
    cols = {str(c).strip().lower(): c for c in data.columns}
    c_parent = cols.get('kode induk')
    c_seg = cols.get('segment')
    c_uraian = cols.get('uraian')
    c_kode = cols.get('kode referensi')
    c_satuan = cols.get('satuan')
    c_koef = cols.get('koefisien')

    seg_map = {'A': 'A', 'B': 'B', 'C': 'C', 'TK': 'A', 'BHN': 'B', 'PR': 'C', 'LAIN': 'LAIN', 'LAINNYA': 'LAIN'}
    count = 0
    for _, row in data.iterrows():
        parent = normalize_ahsp_code(cell(row, c_parent))
        if not parent:
            continue
        seg = seg_map.get(cell(row, c_seg).upper())
        if not seg:
            continue  # skip non-standard segments (UK/LL/ANOMALI) for clean DB import
        uraian = cell(row, c_uraian)
        if not uraian or uraian == '-':
            continue
        try:
            koef = float(cell(row, c_koef).replace(',', '.'))
        except ValueError:
            koef = 0
        _create_staging_row(
            user=user, batch=batch, file_name=file_name, sumber=sumber,
            parent_ahsp_code=parent, segment_type=seg,
            kode_item=cell(row, c_kode) or '-', uraian_item=uraian,
            satuan_item=cell(row, c_satuan) or '-', koefisien=koef, is_valid=True,
        )
        count += 1
    return count


def _stage_rincian_from_interchange(user, file_name, file_obj, sumber, batch=None):
    """Stage rincian from AHSP Interchange v1 workbook."""
    rows, meta = load_interchange_workbook_rows(file_obj)
    effective_sumber = sumber or (meta.get("sumber") or "").strip()
    validation_rows = [
        {
            "parent_code": row["kode_ahsp"],
            "segment": row["segmen"],
            "no": row.get("no", ""),
            "uraian": row["uraian"],
            "kode_ref": row["kode_item"],
            "satuan": row["satuan"],
            "koefisien": row["koefisien"],
        }
        for row in rows
    ]
    validation = validate_frontend_payload(validation_rows)
    if validation["skipped_tables"]:
        preview = "; ".join(
            f"{item['parent_code']} ({', '.join(item['reasons'])})"
            for item in validation["skipped_tables"][:5]
        )
        extra = f" dan {len(validation['skipped_tables']) - 5} tabel lain" if len(validation["skipped_tables"]) > 5 else ""
        raise ValueError(
            f"Import ditolak: {len(validation['skipped_tables'])} tabel masih warning/anomali. {preview}{extra}"
        )

    titles_by_parent = {}
    for row in rows:
        titles_by_parent.setdefault(row["kode_ahsp"], row.get("nama_ahsp") or row["kode_ahsp"])

    for parent_code, title in titles_by_parent.items():
        _create_staging_row(
            user=user, batch=batch, file_name=file_name, sumber=effective_sumber,
            segment_type='HEADING', kode_item=parent_code,
            uraian_item=title or parent_code, parent_ahsp_code=None, is_valid=True,
        )

    count = 0
    for row in rows:
        _create_staging_row(
            user=user, batch=batch, file_name=file_name, sumber=effective_sumber,
            parent_ahsp_code=row["kode_ahsp"], segment_type=row["segmen"],
            kode_item=row["kode_item"] or "-", uraian_item=row["uraian"],
            satuan_item=row["satuan"] or "-", koefisien=row["koefisien"] or 0,
            is_valid=True,
        )
        count += 1
    return count, effective_sumber


def _stage_rincian_legacy_flat(user, file_name, df, sumber, batch=None):
    """Legacy positional parser for arbitrary flat clean-Excel files.

    Headings (klasifikasi/sub-klasifikasi/bare parent title) are detected by the
    AHSP code helper; data rows carry the parent code in column 0.
    """
    import pandas as pd

    imported_count = 0
    for _idx, row in df.iterrows():
        row_values = [str(v).strip() for v in row if pd.notna(v) and str(v).strip()]
        if not row_values:
            continue
        row_text = " ".join(row_values)
        first_col = row_values[0]
        first_token = first_col.split(' ')[0] if first_col else ""

        token_class = classify_ahsp_code(first_token)
        has_data_columns = len(row_values) >= 3
        is_heading = (
            token_class == CLASSIFICATION
            or (token_class in (SUBCLASSIFICATION, PARENT) and not has_data_columns)
        )
        if is_heading:
            uraian = " ".join(row_values).replace(first_token, "").strip()
            _create_staging_row(
                user=user, batch=batch, file_name=file_name, sumber=sumber,
                segment_type='HEADING', kode_item=first_token,
                uraian_item=uraian or first_token, parent_ahsp_code=None, is_valid=True,
            )
            continue

        # Data rows: require a valid parent code in column 0.
        parent_code = first_col
        if len(row_values) < 3:
            continue
        if 'uraian' in row_text.lower() and 'kode' in row_text.lower():
            continue
        if 'jumlah' in row_text.lower():
            continue
        parent_class = classify_ahsp_code(parent_code)
        if parent_class not in (SUBCLASSIFICATION, PARENT):
            continue

        col_1_val = row_values[1] if len(row_values) > 1 else ""
        if col_1_val in ['A', 'B', 'C', 'LAIN', 'UK', 'LL']:
            curr_segment = col_1_val
            curr_kode_item = row_values[2] if len(row_values) > 2 else ""
            curr_uraian = row_values[3] if len(row_values) > 3 else ""
            curr_satuan = row_values[4] if len(row_values) > 4 else ""
        else:
            curr_segment = None
            curr_kode_item = col_1_val
            curr_uraian = row_values[2] if len(row_values) > 2 else ""
            curr_satuan = row_values[3] if len(row_values) > 3 else ""

        seg_type = curr_segment if curr_segment else 'A'
        if not curr_segment:
            if 'L.' in curr_kode_item.upper() or 'MANDOR' in curr_uraian.upper():
                seg_type = 'A'
            elif 'B.' in curr_kode_item.upper() or 'SEMEN' in curr_uraian.upper():
                seg_type = 'B'
            elif 'E.' in curr_kode_item.upper() or 'ALAT' in curr_uraian.upper():
                seg_type = 'C'

        koef = 0
        for val in reversed(row_values):
            try:
                koef = float(val.replace(',', '.'))
                break
            except ValueError:
                pass

        _create_staging_row(
            user=user, batch=batch, file_name=file_name, sumber=sumber,
            parent_ahsp_code=parent_code, segment_type=seg_type,
            kode_item=curr_kode_item, uraian_item=curr_uraian,
            satuan_item=curr_satuan or '-', koefisien=koef, is_valid=True,
        )
        imported_count += 1
    return imported_count


@login_required
@user_passes_test(is_admin)
def excel_clean_upload(request):
    """
    Opsi 3: Upload clean Excel for direct import to staging.
    """
    if request.method == 'POST':
        files = request.FILES.getlist('excel_file')

        if not files:
            messages.error(request, "Tidak ada file yang diupload.")
            return redirect('referensi:import_excel')

        invalid = [f.name for f in files if not f.name.lower().endswith(('.xlsx', '.xls'))]
        if invalid:
            messages.error(
                request,
                f"File harus berformat Excel (.xlsx/.xls): {', '.join(invalid[:5])}",
            )
            return redirect('referensi:import_excel')

        # Source/version declared by the user; the parsed Excel may carry it in Meta.
        sumber = (request.POST.get('sumber') or '').strip()
        file_names = [f.name for f in files]
        batch_label = file_names[0] if len(files) == 1 else f"{len(files)} file ({file_names[0]} ...)"
        batch = None

        # Parse and import to staging (multiple files merge into ONE batch).
        try:
            import pandas as pd
            from io import BytesIO

            # Replace prior staging for these files and retire their old STAGED batches.
            old_batch_ids = [
                bid for bid in (
                    AHSPImportStaging.objects.filter(user=request.user, file_name__in=file_names)
                    .values_list('batch_id', flat=True).distinct()
                ) if bid
            ]
            if old_batch_ids:
                AHSPImportBatch.objects.filter(
                    user=request.user, id__in=old_batch_ids,
                    status=AHSPImportBatch.Status.STAGED,
                ).update(status=AHSPImportBatch.Status.CLEARED)
            AHSPImportStaging.objects.filter(user=request.user, file_name__in=file_names).delete()

            batch = AHSPImportBatch.objects.create(
                user=request.user, file_name=batch_label, sumber=sumber,
            )

            imported_count = 0
            effective_sumber = sumber
            for f in files:
                file_bytes = f.read()
                if is_interchange_workbook(BytesIO(file_bytes)):
                    cnt, found_sumber = _stage_rincian_from_interchange(
                        request.user, f.name, BytesIO(file_bytes), sumber, batch=batch
                    )
                    if found_sumber:
                        effective_sumber = found_sumber
                    imported_count += cnt
                else:
                    xls = pd.ExcelFile(BytesIO(file_bytes))
                    sheet_names = list(xls.sheet_names)
                    # The validation/export output stores rincian in a "Data Valid"/
                    # "Data Anomali"/"Data" sheet ("Daftar Isi" is sheet 0); pick the right one.
                    data_sheet = next(
                        (n for n in sheet_names if n.strip().lower() in ('data valid', 'data anomali', 'data')),
                        sheet_names[0],
                    )
                    peek = pd.read_excel(xls, sheet_name=data_sheet, header=None, nrows=1)
                    header_cells = [str(v).strip().lower() for v in peek.iloc[0].tolist()] if len(peek) else []
                    is_export_format = 'kode induk' in header_cells and 'segment' in header_cells
                    if is_export_format:
                        imported_count += _stage_rincian_from_export(
                            request.user, f.name, xls, data_sheet, sheet_names, sumber, batch=batch
                        )
                    else:
                        df = pd.read_excel(xls, sheet_name=data_sheet, header=None)
                        imported_count += _stage_rincian_legacy_flat(
                            request.user, f.name, df, sumber, batch=batch
                        )

            if effective_sumber and batch.sumber != effective_sumber:
                batch.sumber = effective_sumber
                batch.save(update_fields=["sumber"])

            blocked_tables = _blocked_staging_tables(request.user, batch=batch)
            if blocked_tables:
                AHSPImportStaging.objects.filter(user=request.user, batch=batch).delete()
                batch.status = AHSPImportBatch.Status.FAILED
                batch.summary = {"blocked_tables": blocked_tables}
                batch.save(update_fields=["status", "summary"])
                preview = "; ".join(
                    f"{item['parent_code']} ({', '.join(item['reasons'])})"
                    for item in blocked_tables[:5]
                )
                extra = f" dan {len(blocked_tables) - 5} tabel lain" if len(blocked_tables) > 5 else ""
                messages.error(
                    request,
                    f"Import ditolak: {len(blocked_tables)} tabel belum lengkap/masih warning. {preview}{extra}"
                )
                return redirect('referensi:import_excel')

            file_note = f" dari {len(files)} file" if len(files) > 1 else ""
            messages.success(request, f"Import berhasil! {imported_count} rincian{file_note} masuk staging.")
            return redirect('referensi:import_staging')

        except Exception as e:
            if batch is not None:
                AHSPImportStaging.objects.filter(user=request.user, batch=batch).delete()
                batch.status = AHSPImportBatch.Status.FAILED
                batch.summary = {"error": str(e)}
                batch.save(update_fields=["status", "summary"])
            messages.error(request, f"Error import: {str(e)}")

        return redirect('referensi:import_excel')

    return render(request, 'referensi/import_excel.html')


# =============================================================================
# SHARED: STAGING VIEW
# =============================================================================

def _blocked_staging_tables(user, file_name=None, batch=None):
    queryset = AHSPImportStaging.objects.filter(user=user, is_valid=True, segment_type__in=['A', 'B', 'C', 'LAIN'])
    if file_name:
        queryset = queryset.filter(file_name=file_name)
    if batch is not None:
        queryset = queryset.filter(batch=batch)

    rows_by_parent = {}
    for item in queryset:
        rows_by_parent.setdefault(item.parent_ahsp_code, []).append({
            "parent_code": item.parent_ahsp_code or "",
            "segment": item.segment_type,
            "no": item.kode_item,
            "uraian": item.uraian_item,
            "kode_ref": item.kode_item,
            "satuan": item.satuan_item,
            "koefisien": str(item.koefisien),
            "row_id": str(item.id),
        })

    blocked = []
    for parent_code, rows in rows_by_parent.items():
        status = compute_block_status({"rows": rows})
        if status["is_blocked"]:
            blocked.append({
                "parent_code": parent_code or "-",
                "reasons": status["blocked_reasons"],
                "row_count": len(rows),
            })
    return blocked


def _get_active_import_batch(user, batch_id=None):
    if batch_id:
        return AHSPImportBatch.objects.filter(user=user, id=batch_id).first()
    queryset = AHSPImportBatch.objects.filter(user=user, status=AHSPImportBatch.Status.STAGED)
    return queryset.filter(rows__isnull=False).distinct().order_by('-created_at', '-id').first()


def _staging_queryset_for_batch(user, batch=None):
    queryset = AHSPImportStaging.objects.filter(user=user)
    if batch is not None:
        return queryset.filter(batch=batch)
    return queryset.filter(batch__isnull=True)


def _commit_preflight(staging_items, sumber, commit_mode):
    from referensi.models import AHSPReferensi, RincianReferensi

    parent_codes = [
        code for code in staging_items.order_by().values_list('parent_ahsp_code', flat=True).distinct()
        if code
    ]
    existing_ahsp = {
        ahsp.kode_ahsp: ahsp
        for ahsp in AHSPReferensi.objects.filter(sumber=sumber, kode_ahsp__in=parent_codes)
    }

    staged_keys_by_parent = {}
    new_rincian = 0
    update_rincian = 0
    delete_rincian = 0
    kategori_map = {'A': 'TK', 'B': 'BHN', 'C': 'ALT', 'LAIN': 'LAIN'}
    existing_rincian_keys = set()
    existing_rincian_by_parent = {}

    if existing_ahsp:
        ahsp_id_to_parent = {obj.id: code for code, obj in existing_ahsp.items()}
        for row in RincianReferensi.objects.filter(ahsp_id__in=ahsp_id_to_parent).values(
            'ahsp_id', 'kategori', 'kode_item', 'uraian_item', 'satuan_item'
        ):
            parent_code = ahsp_id_to_parent[row['ahsp_id']]
            key = (
                parent_code,
                row['kategori'],
                row['kode_item'] or '-',
                row['uraian_item'] or '',
                row['satuan_item'] or '-',
            )
            existing_rincian_keys.add(key)
            existing_rincian_by_parent.setdefault(parent_code, set()).add(key[1:])

    for item in staging_items:
        if not item.parent_ahsp_code:
            continue
        kategori = kategori_map.get(item.segment_type, 'LAIN')
        key = (
            kategori,
            item.kode_item or '-',
            item.uraian_item or '',
            item.satuan_item or '-',
        )
        staged_keys_by_parent.setdefault(item.parent_ahsp_code, set()).add(key)
        if item.parent_ahsp_code not in existing_ahsp:
            new_rincian += 1
            continue
        if (item.parent_ahsp_code, *key) in existing_rincian_keys:
            update_rincian += 1
        else:
            new_rincian += 1

    if commit_mode == AHSPImportBatch.CommitMode.REPLACE:
        for parent_code in existing_ahsp:
            staged_keys = staged_keys_by_parent.get(parent_code, set())
            existing_keys = existing_rincian_by_parent.get(parent_code, set())
            delete_rincian += len(existing_keys - staged_keys)

    return {
        "sumber": sumber,
        "commit_mode": commit_mode,
        "parent_total": len(parent_codes),
        "new_ahsp": len(parent_codes) - len(existing_ahsp),
        "existing_ahsp": len(existing_ahsp),
        "new_rincian": new_rincian,
        "update_rincian": update_rincian,
        "delete_rincian": delete_rincian,
        "duplicate_parent_codes": sorted(existing_ahsp.keys()),
    }


@login_required
@user_passes_test(is_admin)
def staging_view(request):
    """
    View staging data for review before commit.
    """
    active_batch = _get_active_import_batch(request.user, request.GET.get('batch'))
    staging_data = _staging_queryset_for_batch(request.user, active_batch).order_by('id')
    
    # Build a parent-grouped, source-ordered list so each parent HEADING is
    # immediately followed by its OWN A/B/C/LAIN rows. Stagers insert all HEADINGs
    # first and all data rows after, so a plain id-order makes every parent look
    # empty; grouping keeps children next to their parent for easy verification.
    items = list(staging_data)

    headings_by_code = {}
    data_by_parent = {}
    parent_order = []
    seen_parents = set()
    for item in items:
        if item.segment_type == 'HEADING':
            code = (item.kode_item or '').strip()
            headings_by_code[code] = item
        else:
            code = (item.parent_ahsp_code or '').strip()
            data_by_parent.setdefault(code, []).append(item)
        if code and code not in seen_parents:
            seen_parents.add(code)
            parent_order.append(code)

    def _annotate(it):
        # Heuristic indent: HEADING by dot-depth; data rows sit one level deeper.
        dots = (it.kode_item or '').count('.')
        if it.segment_type == 'HEADING':
            it.ui_level = max(0, dots - 1) * 20
            it.is_folder = True
        else:
            it.ui_level = 60
            it.is_folder = False
        return it

    annotated_data = []
    for code in parent_order:
        heading = headings_by_code.get(code)
        if heading is not None:
            annotated_data.append(_annotate(heading))
        for data_item in data_by_parent.get(code, []):
            annotated_data.append(_annotate(data_item))

    # Safety net: append any rows not captured above (e.g. headings without code).
    emitted = {id(x) for x in annotated_data}
    for item in items:
        if id(item) not in emitted:
            annotated_data.append(_annotate(item))
    
    files = staging_data.order_by().values_list('file_name', flat=True).distinct()

    default_sumber = (
        (active_batch.sumber if active_batch else '') or
        staging_data.exclude(sumber='').values_list('sumber', flat=True).first() or ''
    )
    commit_mode = request.GET.get('commit_mode') or AHSPImportBatch.CommitMode.MERGE
    staging_items_for_preflight = staging_data.filter(is_valid=True, segment_type__in=['A', 'B', 'C', 'LAIN'])
    commit_preflight = (
        _commit_preflight(staging_items_for_preflight, default_sumber, commit_mode)
        if default_sumber and staging_items_for_preflight.exists()
        else None
    )
    import_batches = AHSPImportBatch.objects.filter(
        user=request.user,
        status=AHSPImportBatch.Status.STAGED,
    ).order_by('-created_at', '-id')
    detail_rows_qs = staging_data.filter(segment_type__in=['A', 'B', 'C', 'LAIN'])
    parent_ahsp_count = detail_rows_qs.exclude(
        parent_ahsp_code__isnull=True,
    ).exclude(parent_ahsp_code='').order_by().values('parent_ahsp_code').distinct().count()

    context = {
        'staging_data': annotated_data,
        'files': list(files),
        'total_items': detail_rows_qs.count(),
        'total_headings': staging_data.filter(segment_type='HEADING').count(),
        'parent_ahsp_count': parent_ahsp_count,
        'total_staging_rows': staging_data.count(),
        'default_sumber': default_sumber,
        'active_batch': active_batch,
        'import_batches': import_batches,
        'commit_mode': commit_mode,
        'commit_preflight': commit_preflight,
    }
    
    return render(request, 'referensi/import_staging.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def staging_clear(request):
    """
    Clear all staging data for current user.
    """
    deleted_count, _ = AHSPImportStaging.objects.filter(user=request.user).delete()
    AHSPImportBatch.objects.filter(
        user=request.user,
        status=AHSPImportBatch.Status.STAGED,
    ).update(status=AHSPImportBatch.Status.CLEARED)
    messages.info(request, f"Semua data staging ({deleted_count} item) telah dihapus.")
    return redirect('referensi:import_staging')


@login_required
@user_passes_test(is_admin)
@require_POST
def staging_commit(request):
    """
    Commit staging data to main database.
    """
    from referensi.models import AHSPReferensi, RincianReferensi

    active_batch = _get_active_import_batch(request.user, request.POST.get('batch_id'))
    staging_scope = _staging_queryset_for_batch(request.user, active_batch)
    staging_items = staging_scope.filter(
        is_valid=True,
        segment_type__in=['A', 'B', 'C', 'LAIN']
    )
    
    if not staging_items.exists():
        messages.warning(request, "Tidak ada data valid untuk di-commit.")
        return redirect('referensi:import_staging')

    # Source/version (e.g. "AHSP 2024") must be declared: the AHSP uniqueness is
    # scoped per (sumber, kode_ahsp), and the parsed Excel does not carry it.
    sumber = (request.POST.get('sumber') or '').strip()
    if not sumber:
        if active_batch and active_batch.sumber:
            sumber = active_batch.sumber.strip()
    if not sumber:
        sumber = next(
            (
                s for s in staging_scope
                .exclude(sumber='').values_list('sumber', flat=True)
            ),
            '',
        ).strip()
    if not sumber:
        messages.error(
            request,
            "Deklarasikan 'Sumber AHSP' (mis. AHSP 2024) terlebih dahulu sebelum commit.",
        )
        return redirect('referensi:import_staging')

    commit_mode = (
        request.POST.get('commit_mode')
        or AHSPImportBatch.CommitMode.MERGE
    )
    valid_modes = {choice[0] for choice in AHSPImportBatch.CommitMode.choices}
    if commit_mode not in valid_modes:
        messages.error(request, "Mode commit tidak valid.")
        return redirect('referensi:import_staging')

    blocked_tables = _blocked_staging_tables(request.user, batch=active_batch)
    if blocked_tables:
        preview = "; ".join(
            f"{item['parent_code']} ({', '.join(item['reasons'])})"
            for item in blocked_tables[:5]
        )
        extra = f" dan {len(blocked_tables) - 5} tabel lain" if len(blocked_tables) > 5 else ""
        messages.error(
            request,
            f"Commit dibatalkan: {len(blocked_tables)} tabel belum lengkap/masih warning. {preview}{extra}"
        )
        return redirect('referensi:import_staging')

    preflight = _commit_preflight(staging_items, sumber, commit_mode)
    if (
        commit_mode == AHSPImportBatch.CommitMode.ABORT_DUPLICATE
        and preflight["existing_ahsp"] > 0
    ):
        preview = ", ".join(preflight["duplicate_parent_codes"][:10])
        extra = f" dan {preflight['existing_ahsp'] - 10} kode lain" if preflight["existing_ahsp"] > 10 else ""
        messages.error(
            request,
            f"Commit dibatalkan: sumber {sumber} sudah memiliki {preflight['existing_ahsp']} kode AHSP yang sama. {preview}{extra}"
        )
        return redirect('referensi:import_staging')
    
    from django.db import transaction
    from django.db.models.signals import post_save, post_delete
    from referensi.services.cache_helpers import ReferensiCache
    from referensi.signals import invalidate_ahsp_cache, invalidate_rincian_cache

    staged_rows = list(staging_items.order_by('id'))
    parent_codes = sorted({item.parent_ahsp_code for item in staged_rows if item.parent_ahsp_code})

    # Prefetch parent titles (one query) instead of a per-parent HEADING lookup.
    headings = {
        h.kode_item: h.uraian_item
        for h in staging_scope.filter(segment_type='HEADING')
    }
    # Materialize staged data rows once and group in Python (avoid per-parent
    # queries that were previously re-evaluated multiple times).
    items_by_parent = {}
    for item in staged_rows:
        items_by_parent.setdefault(item.parent_ahsp_code, []).append(item)

    created_ahsp = 0
    created_rincian = 0
    updated_rincian = 0
    deleted_rincian = 0
    kategori_map = {'A': 'TK', 'B': 'BHN', 'C': 'ALT', 'LAIN': 'LAIN'}

    # PERFORMANCE: the cache-invalidation signals fire on EVERY AHSP/Rincian
    # save -> for a large batch that means thousands of invalidate_all() calls.
    # Suppress them during the bulk commit, run everything in ONE transaction
    # (single fsync, atomic), then invalidate the cache exactly once at the end.
    post_save.disconnect(invalidate_ahsp_cache, sender=AHSPReferensi)
    post_delete.disconnect(invalidate_ahsp_cache, sender=AHSPReferensi)
    post_save.disconnect(invalidate_rincian_cache, sender=RincianReferensi)
    post_delete.disconnect(invalidate_rincian_cache, sender=RincianReferensi)
    try:
        with transaction.atomic():
            existing_ahsp = {
                obj.kode_ahsp: obj
                for obj in AHSPReferensi.objects.select_for_update().filter(
                    sumber=sumber,
                    kode_ahsp__in=parent_codes,
                )
            }

            new_ahsp_objects = []
            ahsp_to_update = []
            for parent_code in parent_codes:
                nama = headings.get(parent_code) or parent_code
                ahsp_obj = existing_ahsp.get(parent_code)
                if ahsp_obj is None:
                    ahsp_obj = AHSPReferensi(
                        kode_ahsp=parent_code,
                        sumber=sumber,
                        nama_ahsp=nama,
                    )
                    new_ahsp_objects.append(ahsp_obj)
                elif nama and nama != parent_code and ahsp_obj.nama_ahsp != nama:
                    ahsp_obj.nama_ahsp = nama
                    ahsp_to_update.append(ahsp_obj)

            if new_ahsp_objects:
                AHSPReferensi.objects.bulk_create(new_ahsp_objects, batch_size=500)
                created_ahsp = len(new_ahsp_objects)
                existing_ahsp.update({obj.kode_ahsp: obj for obj in new_ahsp_objects})
            if ahsp_to_update:
                AHSPReferensi.objects.bulk_update(ahsp_to_update, ["nama_ahsp"], batch_size=500)

            ahsp_id_to_parent = {obj.id: code for code, obj in existing_ahsp.items()}
            existing_rincian = {}
            if ahsp_id_to_parent:
                for rincian in RincianReferensi.objects.filter(
                    ahsp_id__in=ahsp_id_to_parent,
                ).only(
                    "id",
                    "ahsp_id",
                    "kategori",
                    "kode_item",
                    "uraian_item",
                    "satuan_item",
                    "koefisien",
                ):
                    parent_code = ahsp_id_to_parent[rincian.ahsp_id]
                    key = (
                        parent_code,
                        rincian.kategori,
                        rincian.kode_item or '-',
                        rincian.uraian_item or '',
                        rincian.satuan_item or '-',
                    )
                    existing_rincian[key] = rincian

            staged_unique = {}
            for parent_code in parent_codes:
                for item in items_by_parent.get(parent_code, []):
                    kategori = kategori_map.get(item.segment_type, 'LAIN')
                    key = (
                        parent_code,
                        kategori,
                        item.kode_item or '-',
                        item.uraian_item or '',
                        item.satuan_item or '-',
                    )
                    staged_unique[key] = item

            if commit_mode == AHSPImportBatch.CommitMode.REPLACE:
                staged_key_set = set(staged_unique)
                delete_ids = [
                    rincian.id
                    for key, rincian in existing_rincian.items()
                    if key[0] in parent_codes and key not in staged_key_set
                ]
                if delete_ids:
                    deleted_rincian = len(delete_ids)
                    RincianReferensi.objects.filter(id__in=delete_ids).delete()

            to_create = []
            to_update = []
            for key, item in staged_unique.items():
                parent_code, kategori, kode_item, uraian_item, satuan_item = key
                existing = existing_rincian.get(key)
                if existing is None:
                    to_create.append(RincianReferensi(
                        ahsp=existing_ahsp[parent_code],
                        kategori=kategori,
                        kode_item=kode_item,
                        uraian_item=uraian_item,
                        satuan_item=satuan_item,
                        koefisien=item.koefisien,
                    ))
                elif existing.koefisien != item.koefisien:
                    existing.koefisien = item.koefisien
                    to_update.append(existing)

            if to_create:
                RincianReferensi.objects.bulk_create(to_create, batch_size=1000)
                created_rincian = len(to_create)
            if to_update:
                RincianReferensi.objects.bulk_update(to_update, ["koefisien"], batch_size=1000)
            unchanged_existing = len(staged_unique) - len(to_create) - len(to_update)
            updated_rincian = len(to_update) + max(0, unchanged_existing)

            # Clear staging + finalize batch within the same transaction.
            staging_scope.delete()
            if active_batch:
                active_batch.status = AHSPImportBatch.Status.COMMITTED
                active_batch.sumber = sumber
                active_batch.commit_mode = commit_mode
                active_batch.summary = {
                    **preflight,
                    "created_ahsp": created_ahsp,
                    "created_rincian": created_rincian,
                    "updated_rincian": updated_rincian,
                    "deleted_rincian": deleted_rincian,
                }
                active_batch.committed_at = timezone.now()
                active_batch.save(update_fields=["status", "sumber", "commit_mode", "summary", "committed_at"])
    finally:
        post_save.connect(invalidate_ahsp_cache, sender=AHSPReferensi)
        post_delete.connect(invalidate_ahsp_cache, sender=AHSPReferensi)
        post_save.connect(invalidate_rincian_cache, sender=RincianReferensi)
        post_delete.connect(invalidate_rincian_cache, sender=RincianReferensi)
        # One cache invalidation for the whole commit.
        ReferensiCache.invalidate_all()
    
    messages.success(
        request,
        f"Import berhasil! {created_ahsp} AHSP baru, {created_rincian} rincian baru, "
        f"{updated_rincian} rincian update, {deleted_rincian} rincian dihapus."
    )
    return redirect('referensi:admin_portal')


# =============================================================================
# DUAL EXCEL EXPORT FROM VALIDATION
# =============================================================================

@login_required
@user_passes_test(is_admin)
def export_valid_excel(request):
    """
    Export only VALID data rows (no anomalies) to Excel.
    Sheet 1: Hierarchy (Kode + Judul)
    Sheet 2: Data rows
    """
    import pandas as pd
    from io import BytesIO
    
    # Get the validated file path from session
    validated_file = request.session.get('validated_excel_path')
    if not validated_file or not os.path.exists(validated_file):
        messages.error(request, "Tidak ada file yang divalidasi. Silakan validasi ulang.")
        return redirect('referensi:import_validate')
    
    # Get validation results
    results, df_len, counts = _get_validation_results(validated_file)
    # Apply persisted Edit Mode changes so this export matches the report and the
    # "from-frontend" download (single source of truth for saved edits).
    _apply_edits_to_results(results, _load_validation_edits(request.session.get('validation_file_id')))

    # First pass: collect Parent AHSP info (code -> title mapping)
    parent_info = {}  # {code: judul}

    for item in results:
        if item.get('type') == 'hierarchy_parent':
            raw_col = item.get('first_col', '-')
            # Extract clean code (first token) to use as KEY
            clean_code = raw_col.split(' ')[0].strip()
            
            # Get judul from preview
            preview = item.get('preview', raw_col)
            
            # Remove clean_code from the text to get title
            # Handle cases where raw_col involved (like "1.2.3.4 Judul")
            # Try to strip specifically the clean_code
            judul = preview.replace(clean_code, '', 1).strip()
            
            if judul.endswith('...'):
                judul = judul[:-3]
            # Remove potential leading separator like "." or "-" if distinct
            judul = judul.lstrip('.-_ ').strip()
            
            if not judul:
                judul = raw_col # Fallback
                
            parent_info[clean_code] = judul
    
    # Second pass: collect valid data rows and their parent codes
    valid_rows = []
    parent_codes_with_data = set()
    
    for item in results:
        if item.get('type') == 'table_container':
            if not item.get('can_export'):
                continue
            
            grouped_rows = item.get('grouped_rows', {})
            for seg in ['TK', 'BHN', 'PR', 'LAIN']:
                for row_item in grouped_rows.get(seg, []):
                    orig = row_item.get('original_row', {})
                    parent_code = orig.get('col_0', '-')
                    
                    # Track parent codes that have data
                    if parent_code and parent_code != '-':
                        parent_codes_with_data.add(parent_code)
                    
                    valid_rows.append({
                        'Kode Induk': parent_code,
                        'Segment': normalize_segment(orig.get('col_1', '-')),
                        'No': orig.get('col_2', '-'),
                        'Uraian': orig.get('col_3', '-'),
                        'Kode Referensi': orig.get('col_4', '-'),
                        'Satuan': orig.get('col_5', '-'),
                        'Koefisien': orig.get('col_6', '-'),
                    })
    
    if not valid_rows:
        messages.warning(request, "Tidak ada data valid untuk diekspor.")
        return redirect('referensi:import_validate_report')
    
    # Build "Daftar Isi" (TOC) from parent codes with data
    daftar_isi = []
    for code in sorted(parent_codes_with_data):
        daftar_isi.append({
            'Kode AHSP': code,
            'Judul Pekerjaan': parent_info.get(code, code)
        })
    
    # Create Excel with 2 sheets
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Daftar Isi (TOC)
        if daftar_isi:
            df_toc = pd.DataFrame(daftar_isi)
            df_toc.to_excel(writer, index=False, sheet_name='Daftar Isi')
        
        # Sheet 2: Data Valid
        df_data = pd.DataFrame(valid_rows)
        df_data.to_excel(writer, index=False, sheet_name='Data Valid')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="ahsp_valid_data.xlsx"'
    return response


@login_required
@user_passes_test(is_admin)
def export_anomaly_excel(request):
    """
    Export only ANOMALY data rows (UK, LL, or structural anomalies) to Excel.
    Sheet 1: Daftar Isi (Kode AHSP + Judul for anomaly items)
    Sheet 2: Data Anomali with reasons
    """
    import pandas as pd
    from io import BytesIO
    
    # Get the validated file path from session
    validated_file = request.session.get('validated_excel_path')
    if not validated_file or not os.path.exists(validated_file):
        messages.error(request, "Tidak ada file yang divalidasi. Silakan validasi ulang.")
        return redirect('referensi:import_validate')
    
    # Get validation results
    results, df_len, counts = _get_validation_results(validated_file)
    # Apply persisted Edit Mode changes so this export matches the report and the
    # "from-frontend" download (single source of truth for saved edits).
    _apply_edits_to_results(results, _load_validation_edits(request.session.get('validation_file_id')))

    # First pass: collect Parent AHSP info (code -> title mapping)
    parent_info = {}  # {code: judul}

    for item in results:
        if item.get('type') == 'hierarchy_parent':
            raw_col = item.get('first_col', '-')
            # Extract clean code (first token) to use as KEY
            clean_code = raw_col.split(' ')[0].strip()
            
            # Get judul from preview
            preview = item.get('preview', raw_col)
            
            # Remove clean_code from the text to get title
            # Handle cases where raw_col involved (like "1.2.3.4 Judul")
            # Try to strip specifically the clean_code
            judul = preview.replace(clean_code, '', 1).strip()
            
            if judul.endswith('...'):
                judul = judul[:-3]
            # Remove potential leading separator like "." or "-" if distinct
            judul = judul.lstrip('.-_ ').strip()
            
            if not judul:
                judul = raw_col # Fallback
                
            parent_info[clean_code] = judul
    
    # Second pass: collect anomaly data rows and their parent codes
    anomaly_rows = []
    parent_codes_with_anomaly = set()
    
    for item in results:
        if item.get('type') == 'table_container':
            is_blocked = item.get('is_blocked', False)
            blocked_reasons = item.get('blocked_reasons', [])
            grouped_rows = item.get('grouped_rows', {})
            
            if is_blocked:
                reason_text = '; '.join(blocked_reasons) if blocked_reasons else 'Tabel blocked'
                
                for seg in ['TK', 'BHN', 'PR', 'ANOMALI']:
                    for row_item in grouped_rows.get(seg, []):
                        orig = row_item.get('original_row', {})
                        parent_code = orig.get('col_0', '-')
                        
                        # Track parent codes that have anomaly data
                        if parent_code and parent_code != '-':
                            parent_codes_with_anomaly.add(parent_code)
                        
                        anomaly_rows.append({
                            'Kode Induk': parent_code,
                            'Segment': normalize_segment(orig.get('col_1', '-')),
                            'No': orig.get('col_2', '-'),
                            'Uraian': orig.get('col_3', '-'),
                            'Kode Referensi': orig.get('col_4', '-'),
                            'Satuan': orig.get('col_5', '-'),
                            'Koefisien': orig.get('col_6', '-'),
                            'Alasan Anomali': reason_text,
                        })
    
    if not anomaly_rows:
        messages.info(request, "Tidak ada data anomali ditemukan. Semua data valid!")
        return redirect('referensi:import_validate_report')
    
    # Build "Daftar Isi" (TOC) from parent codes with anomaly data
    daftar_isi = []
    for code in sorted(parent_codes_with_anomaly):
        daftar_isi.append({
            'Kode AHSP': code,
            'Judul Pekerjaan': parent_info.get(code, code)
        })
    
    # Create Excel with 2 sheets
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Daftar Isi (TOC)
        if daftar_isi:
            df_toc = pd.DataFrame(daftar_isi)
            df_toc.to_excel(writer, index=False, sheet_name='Daftar Isi')
        
        # Sheet 2: Data Anomali
        df_data = pd.DataFrame(anomaly_rows)
        df_data.to_excel(writer, index=False, sheet_name='Data Anomali')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="ahsp_anomaly_data.xlsx"'
    return response


# =============================================================================
# STATELESS EXPORT (WYSIWYG - What You See Is What You Get)
# =============================================================================

@login_required
@user_passes_test(is_admin)
@require_POST
def repair_preflight(request):
    """
    Validate current WYSIWYG export payload before generating Excel.
    """
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    summary = validate_frontend_payload(data.get('data_rows', []))
    return JsonResponse({
        "valid_parent_codes": summary["valid_parent_codes"],
        "skipped_tables": summary["skipped_tables"],
        "warning_tables": summary["warning_tables"],
        "repair_candidates": summary["repair_candidates"],
        "counts": summary["counts"],
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def export_from_frontend(request):
    """
    Stateless Excel export.
    Frontend sends JSON with current table data (including edits).
    Backend formats it into Excel and returns the file.
    No state saved on server.
    """
    import json
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    
    export_type = data.get('type', 'valid')  # 'valid' or 'anomaly'
    hierarchy = data.get('hierarchy', [])
    data_rows = list(data.get('data_rows', []))

    # Parents present in the DOM payload carry any Edit Mode changes -> keep them.
    dom_parents = {
        str(r.get('parent_code', '')).strip()
        for r in data_rows if str(r.get('parent_code', '')).strip()
    }

    session = getattr(request, 'session', None)
    server_titles = {}

    # Persisted Edit Mode changes from OTHER pages (survive pagination). The DOM
    # of the CURRENT page wins; persisted edits fill in parents not on this page.
    edits = _load_validation_edits(session.get('validation_file_id')) if session is not None else {}
    edit_parents = set()
    for parent, info in (edits or {}).items():
        if not parent or parent in dom_parents:
            continue
        for r in info.get('rows', []):
            uraian = str(r.get('uraian', '') or '').strip()
            if not uraian or uraian == '-':
                continue
            data_rows.append({
                'parent_code': parent,
                'segment': r.get('segment', '-'),
                'no': r.get('no', '-'),
                'uraian': uraian,
                'kode_ref': r.get('kode_ref', '-'),
                'satuan': r.get('satuan', '-'),
                'koefisien': r.get('koefisien', '-'),
            })
        server_titles.setdefault(parent, info.get('title') or parent)
        edit_parents.add(parent)

    covered = dom_parents | edit_parents

    # The report paginates, so tables not on the current page are absent from the
    # DOM. Supplement those (not in DOM and not persisted-edited) from the
    # server-side validated file -> the download stays complete.
    validated_file = session.get('validated_excel_path') if session is not None else None
    if validated_file and os.path.exists(validated_file):
        from referensi.services.ahsp_code import split_ahsp_title
        try:
            server_results, _, _ = _get_validation_results(validated_file)
        except Exception:
            server_results = []
        for item in server_results:
            if item.get('type') == 'hierarchy_parent':
                code, title = split_ahsp_title(str(item.get('first_col', '')))
                if code:
                    server_titles.setdefault(code, title or code)
        for item in server_results:
            if item.get('type') != 'table_container':
                continue
            if export_type == 'valid' and not item.get('can_export'):
                continue
            if export_type == 'anomaly' and not item.get('is_blocked'):
                continue
            parent_code = str(item.get('first_col', '')).split(' ')[0].strip()
            if not parent_code or parent_code in covered:
                continue
            for seg_rows in item.get('grouped_rows', {}).values():
                for row_item in seg_rows:
                    orig = row_item.get('original_row', {})
                    uraian = str(orig.get('col_3', '') or '').strip()
                    if not uraian or uraian == '-':
                        continue  # skip subtotal / empty rows
                    data_rows.append({
                        'parent_code': str(orig.get('col_0', '') or parent_code).strip(),
                        'segment': orig.get('col_1', '-'),
                        'no': orig.get('col_2', '-'),
                        'uraian': uraian,
                        'kode_ref': orig.get('col_4', '-'),
                        'satuan': orig.get('col_5', '-'),
                        'koefisien': orig.get('col_6', '-'),
                    })

    if not data_rows:
        return HttpResponse("No data to export", status=400)

    validation = validate_frontend_payload(data_rows)
    export_rows = validation["valid_rows"] if export_type == "valid" else validation["skipped_rows"]

    if not export_rows:
        return HttpResponse("No data to export", status=400)

    # Title map: DOM hierarchy first (preserves any edits), then server titles
    # for parents only supplied server-side.
    hierarchy_by_code = {}
    for item in hierarchy:
        code = str(item.get('code', '-')).strip()
        if code and code != '-':
            hierarchy_by_code.setdefault(code, item.get('title', '-'))
    for code, title in server_titles.items():
        hierarchy_by_code.setdefault(code, title)

    # Build Data rows
    skipped_reason_by_parent = {
        item["parent_code"]: "; ".join(item["reasons"])
        for item in validation["skipped_tables"]
    }
    formatted_rows = []
    for row in export_rows:
        pcode = row.get('parent_code', '-')
        row_data = {
            'kode_ahsp': pcode,
            'nama_ahsp': hierarchy_by_code.get(pcode, pcode),
            'segmen': row.get('segment', '-'),
            'no': row.get('no', '-'),
            'uraian': row.get('uraian', '-'),
            'kode_item': row.get('kode_ref', '-'),
            'satuan': row.get('satuan', '-'),
            # Koefisien rule: non-numeric is assumed 0 (single source: coerce_koefisien).
            'koefisien': coerce_koefisien(row.get('koefisien')),
            'status': 'blocked' if export_type == 'anomaly' else 'valid',
        }
        if export_type == 'anomaly':
            row_data['alasan'] = skipped_reason_by_parent.get(pcode, '-')
        formatted_rows.append(row_data)

    workbook_bytes = dump_interchange_workbook(
        formatted_rows,
        {
            "sumber": data.get("sumber") or "",
            "export_type": export_type,
        },
    )
    
    filename = 'ahsp_valid_data.xlsx' if export_type == 'valid' else 'ahsp_anomaly_data.xlsx'
    response = HttpResponse(
        workbook_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
