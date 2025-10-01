from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Dict
import os
import fitz  # PyMuPDF

# -------- Configurable shared content base --------
# Set PDF_CONTENT_BASE to something like: D:\SharedContent
BASE_DIR = Path(__file__).resolve().parent.parent
base_env = os.getenv("PDF_CONTENT_BASE")
if base_env and base_env.strip():
    CONTENT_DIR = Path(base_env).expanduser().resolve()
else:
    CONTENT_DIR = (BASE_DIR / "content").resolve()  # local fallback

SUBFOLDERS = ["One", "Two", "Three"]

app = FastAPI(title="Project 2 — PDF Subfolder Processor (Shared)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- helpers ----------
def ensure_dir(p: Path) -> None:
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create directory '{p}': {exc}")

def ensure_content_and_subdirs() -> Dict[str, bool]:
    ensure_dir(CONTENT_DIR)
    state = {}
    for name in SUBFOLDERS:
        d = CONTENT_DIR / name
        ensure_dir(d)
        state[name] = d.exists()
    return state

def list_subfolders_state() -> Dict[str, bool]:
    return {name: (CONTENT_DIR / name).exists() for name in SUBFOLDERS}

def find_pdfs(folder: Path) -> List[Path]:
    return sorted([p for p in folder.glob("*.pdf") if p.is_file()])

def extract_text_from_pdf(pdf_path: Path) -> str:
    with fitz.open(pdf_path) as doc:
        parts = [page.get_text("text") for page in doc]
    return "\n".join(parts).strip()

def safe_filename(name: str) -> str:
    # Drop path components & odd separators
    name = Path(name).name
    return name.replace("\\", "_").replace("/", "_")

# ---------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok", "content_dir": str(CONTENT_DIR), "subfolders": SUBFOLDERS}

@app.post("/init_subfolders")
def init_subfolders():
    created = ensure_content_and_subdirs()
    return {"message": "initialized", "content": str(CONTENT_DIR), "subfolders": created}

@app.get("/subfolders")
def get_subfolders():
    ensure_dir(CONTENT_DIR)
    return {"content": str(CONTENT_DIR), "subfolders": list_subfolders_state()}

@app.get("/list_pdfs/{sub}")
def list_pdfs_in_subfolder(sub: str):
    if sub not in SUBFOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown subfolder. Use one of: {SUBFOLDERS}")
    subdir = CONTENT_DIR / sub
    if not subdir.exists():
        ensure_dir(subdir)
    pdfs = [p.name for p in find_pdfs(subdir)]
    return {"subfolder": sub, "count": len(pdfs), "files": pdfs}

@app.post("/process_subfolders")
def process_subfolders():
    ensure_dir(CONTENT_DIR)
    results = []
    for sub in SUBFOLDERS:
        subdir = CONTENT_DIR / sub
        ensure_dir(subdir)

        pdfs = find_pdfs(subdir)
        if not pdfs:
            results.append({
                "subfolder": sub,
                "status": "no_pdfs",
                "message": f"No PDF files found in {subdir}.",
                "output": None
            })
            continue

        aggregated: List[str] = []
        for pdf in pdfs:
            try:
                text = extract_text_from_pdf(pdf)
                header = f"\n\n===== {pdf.name} =====\n"
                aggregated.append(header + (text if text else "[No extractable text]"))
            except Exception as exc:
                aggregated.append(f"\n\n===== {pdf.name} (ERROR) =====\nExtraction failed: {exc}")

        out_path = subdir / "output.txt"
        try:
            out_path.write_text("".join(aggregated).strip() + "\n", encoding="utf-8")
            results.append({
                "subfolder": sub,
                "status": "ok",
                "pdf_count": len(pdfs),
                "output": str(out_path)
            })
        except Exception as exc:
            results.append({
                "subfolder": sub,
                "status": "write_error",
                "message": f"Failed to write output.txt: {exc}",
                "output": None
            })

    return {"content": str(CONTENT_DIR), "results": results}

@app.get("/download_output/{sub}")
def download_output_txt(sub: str):
    if sub not in SUBFOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown subfolder. Use one of: {SUBFOLDERS}")
    subdir = CONTENT_DIR / sub
    if not subdir.exists():
        raise HTTPException(status_code=404, detail=f"Subfolder '{sub}' does not exist. Run /init_subfolders first.")
    out_path = subdir / "output.txt"
    if not out_path.exists() or not out_path.is_file():
        raise HTTPException(status_code=404, detail=f"output.txt not found in '{sub}'. Run /process_subfolders after adding PDFs.")
    return FileResponse(out_path, media_type="text/plain", filename="output.txt")

# (Optional) Upload directly into a subfolder
@app.post("/upload_to/{sub}")
async def upload_to_subfolder(sub: str, file: UploadFile = File(...)):
    if sub not in SUBFOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown subfolder. Use one of: {SUBFOLDERS}")
    ensure_dir(CONTENT_DIR)
    subdir = CONTENT_DIR / sub
    ensure_dir(subdir)

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    dest_name = safe_filename(file.filename)
    dest = subdir / dest_name
    try:
        with dest.open("wb") as f:
            # UploadFile is async, but reading in one go is fine for small/medium files
            f.write(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {exc}")
    return {"message": "uploaded", "subfolder": sub, "filename": dest_name, "path": str(dest)}
