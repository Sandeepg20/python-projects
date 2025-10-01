# app/db.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql+psycopg://postgres:Pass%40123@127.0.0.1:5432/genai_questions
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Example:\n"
        "postgresql+psycopg://postgres:Pass%40123@127.0.0.1:5432/genai_questions"
    )

def create_database_if_not_exists(db_url: str):
    url = make_url(db_url)
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, pool_pre_ping=True, future=True)
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :d"),
                {"d": url.database},
            ).scalar()
            if not exists:
                conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                    text(f'CREATE DATABASE "{url.database}"')
                )
    finally:
        admin_engine.dispose()

create_database_if_not_exists(DATABASE_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
