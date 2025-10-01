# cli_load_chapter.py
from __future__ import annotations
import argparse, json, os, sys
from typing import Any, List, Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, Session, Mapped, mapped_column
from sqlalchemy.types import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON as PGJSON

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print(
        "ERROR: DATABASE_URL not set. Example:\n"
        "  postgresql+psycopg://postgres:Pass%40123@127.0.0.1:5432/genai_questions",
        file=sys.stderr,
    )
    sys.exit(4)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
Base = declarative_base()

class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_name: Mapped[Optional[str]] = mapped_column(String(200))
    chapter_name: Mapped[Optional[str]] = mapped_column(String(200))
    question_text: Mapped[str] = mapped_column(Text)
    answer_options: Mapped[Optional[Any]] = mapped_column(PGJSON, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(512))

def coerce_options(val: Any) -> List[str]:
    if val is None: return []
    if isinstance(val, list): return [str(x) for x in val]
    if isinstance(val, str):
        try:
            data = json.loads(val)
            if isinstance(data, list): return [str(x) for x in data]
        except Exception:
            return [val]
    return [str(val)]

def main() -> int:
    ap = argparse.ArgumentParser(description="Print all questions for a chapter (standalone).")
    ap.add_argument("--chapter", required=True, help="Chapter name (non-empty).")
    ap.add_argument("--subject", help="Optional subject filter.")
    ap.add_argument("--case-insensitive", action="store_true", help="Case-insensitive match.")
    ap.add_argument("--limit", type=int, help="Limit rows.")
    args = ap.parse_args()

    chapter = (args.chapter or "").strip()
    if not chapter:
        print("ERROR: Chapter name cannot be empty.", file=sys.stderr)
        return 2

    try:
        with Session(engine) as db:
            stmt = select(
                Question.id, Question.subject_name, Question.chapter_name,
                Question.question_text, Question.answer_options, Question.source_file
            )
            if args.case_insensitive:
                stmt = stmt.where(Question.chapter_name.ilike(chapter))
                if args.subject: stmt = stmt.where(Question.subject_name.ilike(args.subject.strip()))
            else:
                stmt = stmt.where(Question.chapter_name == chapter)
                if args.subject: stmt = stmt.where(Question.subject_name == args.subject.strip())
            stmt = stmt.order_by(Question.id.desc())
            if args.limit and args.limit > 0: stmt = stmt.limit(args.limit)
            rows = db.execute(stmt).all()
    except Exception as exc:
        print(f"ERROR: DB query failed: {exc}", file=sys.stderr)
        return 4

    if not rows:
        print(f"No questions found for chapter='{chapter}'" + (f" and subject='{args.subject}'" if args.subject else "") + ".")
        return 3

    print("=" * 80)
    title = f"Questions for chapter='{chapter}'" + (f", subject='{args.subject.strip()}'" if args.subject else "")
    if args.case_insensitive: title += " (case-insensitive)"
    print(title)
    print("=" * 80)

    for idx, (qid, subj, chap, qtext, opts_raw, src) in enumerate(rows, 1):
        print(f"\n#{idx}  (id={qid}) — {subj or ''} / {chap or ''}")
        print(qtext.strip() if qtext else "[no question text]")
        opts = coerce_options(opts_raw)
        if opts:
            for i, opt in enumerate(opts, 1):
                print(f"  {i}. {opt}")
        if src: print(f"  — source: {src}")
    print("\nDone.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
