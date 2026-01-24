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


def list_students() -> None:
    """List all students and their session info."""
    from sqlalchemy import select, func

    init_db()

    with SessionLocal() as db:
        # Get all unique students with their session counts and scores
        results = db.execute(
            select(
                Session.student_id,
                func.count(Session.id).label("session_count"),
                func.max(Session.score).label("best_score"),
                func.max(Session.score_max).label("score_max"),
                func.max(Session.started_at).label("last_session"),
            )
            .group_by(Session.student_id)
            .order_by(Session.student_id)
        ).all()

        if not results:
            print("No students found.")
            return

        print("\n" + "="*70)
        print("ALL STUDENTS")
        print("="*70)
        print(f"{'Student ID':<30} {'Sessions':<10} {'Best Score':<15} {'Last Session'}")
        print("-"*70)

        for row in results:
            score_str = f"{row.best_score}/{row.score_max}" if row.best_score is not None else "N/A"
            last_session = row.last_session.strftime("%Y-%m-%d %H:%M") if row.last_session else "N/A"
            print(f"{row.student_id:<30} {row.session_count:<10} {score_str:<15} {last_session}")

        print("-"*70)
        print(f"Total: {len(results)} students\n")


if __name__ == "__main__":
    list_students()
