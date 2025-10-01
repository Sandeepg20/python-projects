"""
Usage (Windows PowerShell examples):

# Using shared folder D:\SharedContent (recommended)
$env:PDF_CONTENT_BASE = "D:\SharedContent"
python cli_read_page.py --file "Chemistry Questions.pdf" --page 2

# Optional: if your PDFs live inside a subfolder (like Project 2):
python cli_read_page.py --file "doc.pdf" --page 1 --sub One
"""
from pathlib import Path
import argparse
import os
import sys
import fitz  # PyMuPDF

def resolve_content_dir() -> Path:
    base_env = os.getenv("PDF_CONTENT_BASE")
    base_dir = Path(__file__).resolve().parent
    if base_env and base_env.strip():
        return Path(base_env).expanduser().resolve()
    return (base_dir / "content").resolve()

def ensure_dir(p: Path) -> None:
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(f"ERROR: Failed to create directory '{p}': {exc}", file=sys.stderr)
        sys.exit(1)

def safe_filename(name: str) -> str:
    name = Path(name).name
    return name.replace("\\", "_").replace("/", "_")

def extract_single_page_text(pdf_path: Path, page_num: int) -> str:
    with fitz.open(pdf_path) as doc:
        if page_num < 1 or page_num > doc.page_count:
            raise ValueError(f"Page number out of range. This document has {doc.page_count} pages.")
        page = doc.load_page(page_num - 1)  # 0-based index internally
        txt = page.get_text("text").strip()
        return txt if txt else "[No extractable text on this page]"

def main():
    parser = argparse.ArgumentParser(
        description="Read text from a specific page of a PDF and write to output.txt"
    )
    parser.add_argument("--file", required=True, help="PDF filename (e.g., 'doc.pdf')")
    parser.add_argument("--page", type=int, required=True, help="1-based page number to extract")
    parser.add_argument("--sub", help="Optional subfolder (e.g., One, Two, Three)")
    args = parser.parse_args()

    content_dir = resolve_content_dir()
    ensure_dir(content_dir)

    # If a subfolder is specified, use it (Project 2 style)
    if args.sub:
        content_dir = content_dir / args.sub
        ensure_dir(content_dir)

    pdf_name = safe_filename(args.file)
    pdf_path = content_dir / pdf_name

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        print(f"ERROR: PDF not found at '{pdf_path}'.", file=sys.stderr)
        sys.exit(2)

    try:
        text = extract_single_page_text(pdf_path, args.page)
    except ValueError as ve:
        print(f"ERROR: {ve}", file=sys.stderr)
        sys.exit(3)
    except Exception as exc:
        print(f"ERROR: Failed to read PDF: {exc}", file=sys.stderr)
        sys.exit(4)

    output_txt = content_dir / "output.txt"
    try:
        output_txt.write_text(text, encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: Failed to write output.txt: {exc}", file=sys.stderr)
        sys.exit(5)

    print(f"OK: Wrote page {args.page} of '{pdf_name}' to '{output_txt}'")

if __name__ == "__main__":
    main()
