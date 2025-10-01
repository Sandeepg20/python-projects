# app/models.py
from __future__ import annotations

import datetime as dt
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, func, JSON, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class QuestionBase(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 'subjective' | 'true_false' | 'mcq'
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    subject_name: Mapped[str] = mapped_column(String(200), nullable=False)
    chapter_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # MCQ uses this; TF/subjective may ignore
    answer_options: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    source_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "base",
    }


class SubjectiveQuestion(QuestionBase):
    __tablename__ = "questions_subjective"

    id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    suggested_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # optional parent relationship (not strictly required)
    parent: Mapped[QuestionBase] = relationship("QuestionBase", viewonly=True)

    __mapper_args__ = {"polymorphic_identity": "subjective"}


class TrueFalseQuestion(QuestionBase):
    __tablename__ = "questions_truefalse"

    id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    option_true_label: Mapped[str] = mapped_column(String(16), default="True")
    option_false_label: Mapped[str] = mapped_column(String(16), default="False")
    correct_is_true: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    parent: Mapped[QuestionBase] = relationship("QuestionBase", viewonly=True)

    __mapper_args__ = {"polymorphic_identity": "true_false"}


class MCQQuestion(QuestionBase):
    __tablename__ = "questions_mcq"

    id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    # store indices of correct options if you want (optional)
    correct_indices: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    parent: Mapped[QuestionBase] = relationship("QuestionBase", viewonly=True)

    __mapper_args__ = {"polymorphic_identity": "mcq"}
