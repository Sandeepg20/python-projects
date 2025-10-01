# ADD at top with other imports
import json, re
from typing import Optional
from fastapi import Query

# ---------- existing helper in Project 3 (keep as-is) ----------
def extract_pdf_page_text(pdf_path: Path, page_num: int) -> str:
    """Extract text from a single page (1-based page_num)."""
    with fitz.open(pdf_path) as doc:
        if page_num < 1 or page_num > doc.page_count:
            raise HTTPException(status_code=400, detail=f"Page number out of range (1..{doc.page_count}).")
        page = doc.load_page(page_num - 1)
        txt = page.get_text("text").strip()
        return txt if txt else "[No extractable text on this page]"

# ---------- NEW helpers for regex config ----------
def resolve_target_dir(sub: Optional[str]) -> Path:
    """
    Returns CONTENT_DIR or CONTENT_DIR/<sub> if provided (1-level only),
    creating the folder when needed.
    """
    ensure_content_dir()
    base = PDF_CONTENT_DIR
    if sub:
        safe_sub = Path(sub).name  # avoid traversal
        base = base / safe_sub
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create directory '{base}': {exc}")
    return base

_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "UNICODE": re.UNICODE,
    "ASCII": re.ASCII,
    "VERBOSE": re.VERBOSE,
}

def compile_regex_from_config(config_path: Path) -> re.Pattern:
    """
    Load {"regex": "...", "flags": ["IGNORECASE","MULTILINE",...]} from JSON and compile.
    Raises HTTPException with clear messages for all error cases.
    """
    if not config_path.exists() or not config_path.is_file():
        raise HTTPException(status_code=404, detail=f"Config file not found at '{config_path}'.")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse config JSON: {exc}")

    pattern = data.get("regex")
    if not isinstance(pattern, str) or not pattern.strip():
        raise HTTPException(status_code=400, detail="Config is missing 'regex' string.")

    flags_val = 0
    flags = data.get("flags", [])
    if flags:
        if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
            raise HTTPException(status_code=400, detail="'flags' must be a list of strings.")
        for name in flags:
            if name.upper() not in _FLAG_MAP:
                raise HTTPException(status_code=400, detail=f"Unknown regex flag: {name}")
            flags_val |= _FLAG_MAP[name.upper()]

    try:
        return re.compile(pattern, flags_val)
    except re.error as exc:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {exc}")

# ---------- NEW endpoint: read page, apply regex, write output.txt ----------
@app.post("/extract_page_regex_to_output/{filename}")
def extract_page_regex_to_output(
    filename: str,
    page: int = Query(..., gt=0, description="1-based page number to extract"),
    sub: Optional[str] = Query(None, description="Optional subfolder (e.g., One/Two/Three)"),
    config: Optional[str] = Query(None, description="Config path (JSON). Defaults to 'config.json' in target folder.")
):
    """
    Read text from just one page, filter it by regex read from a config JSON, and write to output.txt.
    - Default config path: <CONTENT_DIR[/sub]>/config.json
    - Config format:
        {
          "regex": "\\\\bQ\\\\d+\\.",
          "flags": ["IGNORECASE", "MULTILINE"]   # optional
        }
    """
    target_dir = resolve_target_dir(sub)

    # resolve config path
    cfg_path = Path(config) if config else (target_dir / "config.json")
    if not cfg_path.is_absolute():
        cfg_path = (target_dir / cfg_path).resolve()

    # prepare PDF path
    name = safe_filename(filename)
    pdf_path = (target_dir / name) if sub else (PDF_CONTENT_DIR / name)
    if (not pdf_path.exists()) or (not pdf_path.is_file()) or pdf_path.suffix.lower() != ".pdf":
        where = f"{target_dir}" if sub else f"{PDF_CONTENT_DIR}"
        raise HTTPException(status_code=404, detail=f"PDF not found at '{where}/{name}'.")

    # read page text
    try:
        full_text = extract_pdf_page_text(pdf_path, page)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read page: {exc}")

    # compile regex
    pattern = compile_regex_from_config(cfg_path)

    # apply regex (keep the exact matched spans)
    matches = [m.group(0) for m in pattern.finditer(full_text)]
    final_text = "\n".join(matches).strip() if matches else "[No regex matches]"

    # write output
    out_path = target_dir / "output.txt"
    try:
        out_path.write_text(final_text, encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write output.txt: {exc}")

    return {
        "message": "extracted",
        "pdf": pdf_path.name,
        "page": page,
        "subfolder": sub or "",
        "config": str(cfg_path),
        "matches": len(matches),
        "output": str(out_path),
        "chars": len(final_text),
    }
