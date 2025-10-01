# app/main.py
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Dict, Optional
import os, json, re
import fitz  # PyMuPDF
from sqlalchemy.orm import Session

from .db import get_db, Base, engine
from .models import Question

# ---- create tables once ----
Base.metadata.create_all(bind=engine)

# ---------------- content folder ----------------
BASE_DIR = Path(__file__).resolve().parent.parent
base_env = os.getenv("PDF_CONTENT_BASE")
PDF_CONTENT_DIR = Path(base_env).expanduser().resolve() if base_env and base_env.strip() else (BASE_DIR / "content").resolve()

def ensure_content_dir() -> None:
    try:
        PDF_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create content dir: {exc}")

def safe_filename(name: str) -> str:
    name = Path(name).name
    return name.replace("\\", "_").replace("/", "_")

# ---------------- PDF helpers ----------------
def extract_pdf_text_range(pdf_path: Path, start_page: Optional[int], end_page: Optional[int]) -> str:
    """Extract text for full PDF or page range (1-based, inclusive)."""
    with fitz.open(pdf_path) as doc:
        s = start_page or 1
        e = end_page or doc.page_count
        if s < 1 or e < 1 or s > e or e > doc.page_count:
            raise HTTPException(status_code=400, detail=f"Invalid page range. Document has {doc.page_count} pages.")
        parts = [doc.load_page(i).get_text("text") for i in range(s - 1, e)]
    return "\n".join(parts).strip()

# ---------------- regex helpers ----------------
_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE, "MULTILINE": re.MULTILINE, "DOTALL": re.DOTALL,
    "UNICODE": re.UNICODE, "ASCII": re.ASCII, "VERBOSE": re.VERBOSE,
}

def compile_pattern(pattern: str, flags: Optional[List[str]]) -> re.Pattern:
    flags_val = 0
    for name in flags or []:
        up = name.upper()
        if up not in _FLAG_MAP:
            raise HTTPException(status_code=400, detail=f"Unknown regex flag: {name}")
        flags_val |= _FLAG_MAP[up]
    try:
        return re.compile(pattern, flags_val)
    except re.error as exc:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {exc}")

def load_regex_config(cfg_path: Path) -> Dict:
    if not cfg_path.exists() or not cfg_path.is_file():
        raise HTTPException(status_code=404, detail=f"Config file not found at '{cfg_path}'.")
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse config JSON: {exc}")
    if not isinstance(data.get("question_regex"), str) or not data["question_regex"].strip():
        raise HTTPException(status_code=400, detail="Config is missing 'question_regex' string.")
    if not isinstance(data.get("option_regex"), str) or not data["option_regex"].strip():
        raise HTTPException(status_code=400, detail="Config is missing 'option_regex' string.")
    data.setdefault("question_flags", [])
    data.setdefault("option_flags", [])
    return data

def parse_questions_with_config(full_text: str, cfg: Dict) -> List[Dict]:
    """
    question_regex finds each question block; if it has (?P<question>...), use that group, else the whole block.
    option_regex finds options in the block; if it has (?P<option>...), use that group, else the whole match.
    """
    q_pat = compile_pattern(cfg["question_regex"], cfg.get("question_flags"))
    o_pat = compile_pattern(cfg["option_regex"], cfg.get("option_flags"))
    results: List[Dict] = []
    for q_match in q_pat.finditer(full_text):
        block = q_match.group(0)
        q_text = q_match.groupdict().get("question", block).strip()
        opts: List[str] = []
        for o_match in o_pat.finditer(block):
            opt_text = o_match.groupdict().get("option", o_match.group(0)).strip()
            if opt_text:
                opts.append(opt_text)
        results.append({"question": q_text, "options": opts})
    return results

# ---------------- FastAPI ----------------
app = FastAPI(title="Project 5 — Questions to PostgreSQL", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"status": "ok", "content_dir": str(PDF_CONTENT_DIR), "db": "ok"}

@app.post("/ingest_pdf_questions/{filename}")
def ingest_pdf_questions(
    filename: str,
    subject: str = Query(..., description="Subject name"),
    chapter: Optional[str] = Query(None, description="Chapter name"),
    page_from: Optional[int] = Query(None, gt=0, description="Start page (1-based)"),
    page_to: Optional[int] = Query(None, gt=0, description="End page (1-based)"),
    config: Optional[str] = Query(None, description="Config JSON path; defaults to 'config.json' next to the PDF"),
    db: Session = Depends(get_db),
):
    ensure_content_dir()
    # resolve PDF
    name = safe_filename(filename)
    pdf_path = PDF_CONTENT_DIR / name
    if not (pdf_path.exists() and pdf_path.is_file() and pdf_path.suffix.lower() == ".pdf"):
        raise HTTPException(status_code=404, detail=f"PDF not found at '{pdf_path}'.")

    # resolve config
    cfg_path = Path(config) if config else (pdf_path.parent / "config.json")
    if not cfg_path.is_absolute():
        cfg_path = (pdf_path.parent / cfg_path).resolve()

    # extract text and parse
    full_text = extract_pdf_text_range(pdf_path, page_from, page_to)
    cfg = load_regex_config(cfg_path)
    items = parse_questions_with_config(full_text, cfg)

    # insert rows
    try:
        for it in items:
            db.add(Question(
                subject_name=subject.strip(),
                chapter_name=(chapter or "").strip() or None,
                question_text=it["question"],
                answer_options=it["options"],  # list -> JSON column
                source_file=str(pdf_path),
                page_start=page_from,
                page_end=page_to,
            ))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB insert failed: {exc}")

    return {
        "message": "ingested",
        "file": str(pdf_path),
        "subject": subject,
        "chapter": chapter or "",
        "page_from": page_from,
        "page_to": page_to,
        "questions_found": len(items),
        "inserted": len(items),
    }
