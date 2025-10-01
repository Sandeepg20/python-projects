# app/main.py
from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import QuestionBase  # ensures models are imported so tables exist
from .schemas import QuestionIn
from .repository import QuestionRepository

# 1) Create the app FIRST
app = FastAPI(title="Project 8 — Polymorphic Questions", version="1.0.0")

# 2) (Optional) CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) Create tables once at startup
Base.metadata.create_all(bind=engine)

# 4) Repo instance
repo = QuestionRepository()

# 5) Routes (now decorators can reference 'app')
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/questions", response_model=dict)
def create_question(payload: QuestionIn, db: Session = Depends(get_db)):
    """
    Store one question of type:
      - subjective
      - true_false
      - mcq
    """
    try:
        obj = repo.add(db, payload)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store question: {exc}")

    return {"message": "created", "id": obj.id, "type": obj.type}
