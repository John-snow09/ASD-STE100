from fastapi import FastAPI, UploadFile, File, Request
from fastapi.templating import Jinja2Templates
from logic.extractor import extract_ste_text
from logic.analyzer import analyze_document
from fastapi.responses import FileResponse
from logic.highlighter import create_highlighted_pdf
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Ensure the upload directory exists
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def dashboard(request: Request):
    # Instead of passing the dict as the second argument, 
    # we use the context= parameter or pass it clearly.
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"results": None}
    )

@app.post("/analyze")
async def analyze_pdf(request: Request, file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    raw_blocks = extract_ste_text(file_path)
    analysis_results = analyze_document(raw_blocks)
    
    # Generate the highlighted PDF
    highlighted_filename = f"STE_{file.filename}"
    create_highlighted_pdf(file_path, analysis_results, file.filename)
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "results": analysis_results, 
            "filename": file.filename,
            "highlighted_file": f"STE_{file.filename}" # This must match the HTML variable
        }
    )

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    return FileResponse(path=file_path, filename=filename, media_type='application/pdf')