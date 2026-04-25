import fitz

def extract_ste_text(pdf_path):
    doc = fitz.open(pdf_path)
    clean_content = []

    for page_num, page in enumerate(doc):
        # --- 1. INITIALIZE TABLE ZONES ---
        # Initialize the list AT THE TOP of each page loop
        table_rects = []

        # A. Find structural tables (Logical check)
        tabs = page.find_tables()
        for t in tabs:
            # We add the whole table area as a "No-Fly Zone"
            table_rects.append(t.bbox) 

        # B. Find vector drawings (Visual check for borders/lines)
        drawings = page.get_drawings()
        for d in drawings:
            if "rect" in d and (d.get("fill") is not None or d.get("stroke") is not None):
                table_rects.append(d["rect"])

        # --- 2. GET TEXT BLOCKS ---
        blocks = page.get_text("blocks")
        
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            text = text.strip()
            
            # Basic validation: ignore images and very short snippets
            if block_type != 0 or len(text) < 10:
                continue

            # --- SHIELD CHECK: Is this block inside a table zone? ---
            block_rect = fitz.Rect(x0, y0, x1, y1)
            is_inside_table = False
            for t_rect in table_rects:
                if block_rect.intersects(t_rect):
                    is_inside_table = True
                    break
            
            if is_inside_table:
                continue # Skip this block entirely if it's in a table zone

            # --- SMART FILTERS: Structural Fingerprinting ---
            
            # 1. THE "TABULAR FINGERPRINT" (High space density)
            spaces = text.count(" ")
            if spaces > 0 and (len(text) / spaces) < 5: 
                continue

            # 2. THE "NUMERIC NOISE" FILTER (Too many numbers/symbols)
            letters = sum(c.isalpha() for c in text)
            if len(text) > 0 and (letters / len(text)) < 0.6:
                continue

            # 3. VERTICAL STACKING CHECK (Tall and narrow = column header)
            if (y1 - y0) > (x1 - x0):
                continue
            
            # 4. PAGE HEADER/FOOTER NOISE
            if text.lower().startswith("page") or "copyright" in text.lower():
                continue
            
            # --- 3. ADD TO CLEAN CONTENT ---
            clean_content.append({
                "page": page_num,
                "text": text.replace("\n", " "),
                "bbox": (x0, y0, x1, y1)
            })
            
    doc.close()
    return clean_content