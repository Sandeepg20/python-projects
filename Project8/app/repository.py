# app/repository.py
from __future__ import annotations
from typing import Protocol
from sqlalchemy.orm import Session
from .models import QuestionBase, SubjectiveQuestion, TrueFalseQuestion, MCQQuestion
from .schemas import QuestionIn, SubjectiveIn, TrueFalseIn, MCQIn

class IQuestionRepository(Protocol):
    def add(self, db: Session, q: QuestionIn) -> QuestionBase: ...

class QuestionRepository(IQuestionRepository):
    def add(self, db: Session, q: QuestionIn) -> QuestionBase:
        if isinstance(q, SubjectiveIn):
            obj = SubjectiveQuestion(
                type="subjective",
                subject_name=q.subject_name.strip(),
                chapter_name=(q.chapter_name or "").strip() or None,
                question_text=q.question_text,
                suggested_answer=q.suggested_answer,
                source_file=q.source_file,
                page_start=q.page_start,
                page_end=q.page_end,
            )
        elif isinstance(q, TrueFalseIn):
            obj = TrueFalseQuestion(
                type="true_false",
                subject_name=q.subject_name.strip(),
                chapter_name=(q.chapter_name or "").strip() or None,
                question_text=q.question_text,
                option_true_label=q.option_true_label,
                option_false_label=q.option_false_label,
                correct_is_true=q.correct_is_true,
                source_file=q.source_file,
                page_start=q.page_start,
                page_end=q.page_end,
            )
        elif isinstance(q, MCQIn):
            obj = MCQQuestion(
                type="mcq",
                subject_name=q.subject_name.strip(),
                chapter_name=(q.chapter_name or "").strip() or None,
                question_text=q.question_text,
                answer_options=q.answer_options,  # stored on base (JSON)
                source_file=q.source_file,
                page_start=q.page_start,
                page_end=q.page_end,
            )
        else:
            raise ValueError("Unsupported question type")

        db.add(obj)
        db.flush()   # get obj.id
        return obj
