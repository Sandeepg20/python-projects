# app/schemas.py
from __future__ import annotations
from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional, Union

class QuestionBaseIn(BaseModel):
    subject_name: str = Field(..., min_length=1)
    chapter_name: Optional[str] = None
    question_text: str = Field(..., min_length=1)
    # Optional provenance
    source_file: Optional[str] = None
    page_start: Optional[int] = Field(None, gt=0)
    page_end: Optional[int] = Field(None, gt=0)

class SubjectiveIn(QuestionBaseIn):
    type: Literal["subjective"] = "subjective"
    suggested_answer: Optional[str] = None

class TrueFalseIn(QuestionBaseIn):
    type: Literal["true_false"] = "true_false"
    # Optional labels (default True/False)
    option_true_label: str = "True"
    option_false_label: str = "False"
    correct_is_true: Optional[bool] = None

class MCQIn(QuestionBaseIn):
    type: Literal["mcq"] = "mcq"
    answer_options: List[str]

    @validator("answer_options")
    def _must_have_at_least_two(cls, v):
        if not v or len(v) < 2:
            raise ValueError("MCQ requires at least two options.")
        return v

# Discriminated union by the 'type' field
QuestionIn = Union[SubjectiveIn, TrueFalseIn, MCQIn]
