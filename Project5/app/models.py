# app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON
from .db import Base

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    subject_name = Column(String(200), nullable=False)
    chapter_name = Column(String(200), nullable=True)
    question_text = Column(Text, nullable=False)
    # stored as real JSON in Postgres
    answer_options = Column(JSON, nullable=True)
    source_file = Column(String(512), nullable=False)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
