import fitz  # PyMuPDF
import os

def create_highlighted_pdf(original_pdf_path, analysis_results, output_filename):
    doc = fitz.open(original_pdf_path)
    
    for error in analysis_results:
        page_num = error["page"]
        page = doc[page_num]
        
        # We search for the original text to get exact visual coordinates
        text_instances = page.search_for(error["original"])
        
        for inst in text_instances:
            # 1. Add Highlight
            annot = page.add_highlight_annot(inst)
            # Yellow is standard for technical reviews, but Red (1, 0, 0) works if you want "Warning" style
            annot.set_colors(stroke=(1, 0.8, 0)) 
            
            # 2. Add the Pop-up Correction Box
            # We put the AI Correction first so it's the first thing they see
            popup_content = f"STE REWRITE:\n{error['correction']}\n\nREASONS:\n" + "\n".join(error["suggestions"])
            
            # add_text_annot creates that little 'sticky note' icon
            # Using inst.tl (top-left) to place it right at the start of the sentence
            sticky_note = page.add_text_annot(inst.tl, popup_content)
            sticky_note.set_info(title="STE COMPLIANCE BOT", content=popup_content)
            
            annot.update()
            sticky_note.update()

    # Save to the uploads folder
    output_path = os.path.join("data", "uploads", f"STE_{output_filename}")
    doc.save(output_path)
    doc.close()
    return output_path