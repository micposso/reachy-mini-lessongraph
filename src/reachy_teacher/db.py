from __future__ import annotations

import os
from datetime import datetime
from sqlalchemy import create_engine, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

SQLITE_PATH = os.getenv("SQLITE_PATH", "reachy_teacher.sqlite")

engine = create_engine(f"sqlite:///{SQLITE_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # lesson_id
    title: Mapped[str] = mapped_column(String)
    plan_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String)
    lesson_id: Mapped[str] = mapped_column(String, ForeignKey("lessons.id"))
    segment_index: Mapped[int] = mapped_column(Integer, default=0)
    transcript_json: Mapped[str] = mapped_column(Text, default="[]")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
