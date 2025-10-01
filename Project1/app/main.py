# app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import shutil
import fitz  # PyMuPDF

# ---------------- Configurable content folder ----------------
# Set PDF_CONTENT_BASE to use a shared folder (e.g., D:\SharedContent)
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
base_env = os.getenv("PDF_CONTENT_BASE")
if base_env and base_env.strip():
    PDF_CONTENT_DIR = Path(base_env).expanduser().resolve()
else:
    PDF_CONTENT_DIR = (BASE_DIR / "content").resolve()

def ensure_content_dir() -> None:
    """Ensure the content directory exists (handles 'folder not available')."""
    try:
        PDF_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create content dir: {exc}")

def safe_filename(name: str) -> str:
    """Drop path components; avoid traversal and odd separators."""
    name = Path(name).name
    return name.replace("\\", "_").replace("/", "_")

# Create at startup (will also re-create on each request via ensure_content_dir)
ensure_content_dir()

app = FastAPI(title="Service for PDF Content", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "content_dir": str(PDF_CONTENT_DIR)}

# 1) Store a PDF in /content
@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    ensure_content_dir()
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    dest_name = safe_filename(file.filename)
    dest = PDF_CONTENT_DIR / dest_name
    try:
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {exc}")

    return {"info": f"file '{dest_name}' saved at '{dest}'"}

# Helper: list PDFs in /content
@app.get("/files")
def list_files():
    ensure_content_dir()
    files = sorted([p.name for p in PDF_CONTENT_DIR.glob("*.pdf") if p.is_file()])
    return {"count": len(files), "files": files}

# 2) Read/Download a PDF from /content
@app.get("/download_pdf/{filename}")
def download_pdf(filename: str):
    ensure_content_dir()
    name = safe_filename(filename)
    file_path = PDF_CONTENT_DIR / name
    if (not file_path.exists()) or (not file_path.is_file()) or file_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF file not found.")
    return FileResponse(path=file_path, filename=name, media_type="application/pdf")

# ---------------- Extract PDF content -> /content/output.txt ----------------
def extract_pdf_text(pdf_path: Path) -> str:
    """Return extracted text from a PDF. Raises if the file can't be opened."""
    with fitz.open(pdf_path) as doc:
        parts = [page.get_text("text") for page in doc]
    return "\n".join(parts).strip()

# 3) Write the content to output.txt (overwrites) under /content
@app.post("/extract_to_output/{filename}")
def extract_to_output(filename: str):
    """
    Reads the specified PDF from /content, writes its text to /content/output.txt.
    Overwrites output.txt if it already exists.
    """
    ensure_content_dir()
    name = safe_filename(filename)
    pdf_path = PDF_CONTENT_DIR / name
    if (not pdf_path.exists()) or (not pdf_path.is_file()) or pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF file not found in /content.")

    try:
        text = extract_pdf_text(pdf_path)
        if not text:
            text = "[No extractable text]"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {exc}")

    output_txt = PDF_CONTENT_DIR / "output.txt"
    try:
        output_txt.write_text(text, encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write output.txt: {exc}")

    return {"message": "extracted", "pdf": pdf_path.name, "output": str(output_txt), "chars": len(text)}

# 4) Download /content/output.txt  (handles 'output.txt not available')
@app.get("/download_output")
def download_output():
    """Download /content/output.txt."""
    ensure_content_dir()
    output_txt = PDF_CONTENT_DIR / "output.txt"
    if not output_txt.exists() or not output_txt.is_file():
        raise HTTPException(status_code=404, detail="output.txt not found. Run extraction first.")
    return FileResponse(path=output_txt, filename="output.txt", media_type="text/plain")
