"""Unified document loader for lessons supporting PDF and Markdown files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader


@dataclass
class Course:
    """Represents a course containing lesson files."""
    name: str
    path: Path
    lesson_files: List[Path]

    @property
    def display_name(self) -> str:
        """Human-readable course name derived from folder name."""
        return self.name.replace("-", " ").replace("_", " ").title()

    @property
    def lesson_count(self) -> int:
        return len(self.lesson_files)


def load_document(file_path: str | Path) -> List[Document]:
    """Load a single document based on its file extension.

    Supports:
        - .pdf: Loaded page-by-page using PyPDFLoader
        - .md: Loaded as plain text using TextLoader

    Args:
        file_path: Path to the document file

    Returns:
        List of Document objects

    Raises:
        ValueError: If file extension is not supported
        FileNotFoundError: If file does not exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    ext = path.suffix.lower()

    if ext == ".pdf":
        return PyPDFLoader(str(path)).load()
    elif ext == ".md":
        docs = TextLoader(str(path), encoding="utf-8").load()
        # Add source metadata similar to PDF loader
        for doc in docs:
            doc.metadata["source"] = str(path)
            doc.metadata["file_type"] = "markdown"
        return docs
    else:
        raise ValueError(f"Unsupported file extension: {ext}. Supported: .pdf, .md")


def load_documents(file_paths: List[str | Path]) -> List[Document]:
    """Load multiple documents from a list of file paths.

    Args:
        file_paths: List of paths to document files

    Returns:
        Combined list of Document objects from all files
    """
    all_docs = []
    for path in file_paths:
        all_docs.extend(load_document(path))
    return all_docs


def discover_lesson_files(lessons_dir: str | Path = "lessons") -> List[Path]:
    """Discover all supported lesson files in a directory (non-recursive).

    Args:
        lessons_dir: Directory to search for lesson files

    Returns:
        List of paths to discovered lesson files (PDF and Markdown)
    """
    path = Path(lessons_dir)
    if not path.exists():
        return []

    files = []
    for ext in ("*.pdf", "*.md"):
        files.extend(path.glob(ext))

    return sorted(files)


def discover_courses(lessons_dir: str | Path = "lessons") -> List[Course]:
    """Discover all courses (subfolders) in the lessons directory.

    Each subfolder is treated as a course containing lesson files.

    Args:
        lessons_dir: Root directory containing course subfolders

    Returns:
        List of Course objects, sorted by name
    """
    path = Path(lessons_dir)
    if not path.exists():
        return []

    courses = []
    for subdir in sorted(path.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith("."):
            lesson_files = discover_lesson_files(subdir)
            if lesson_files:  # Only include courses with lesson files
                courses.append(Course(
                    name=subdir.name,
                    path=subdir,
                    lesson_files=lesson_files
                ))

    return courses


def select_course_interactive(lessons_dir: str | Path = "lessons") -> Optional[Course]:
    """Display an interactive console menu to select a course.

    Args:
        lessons_dir: Root directory containing course subfolders

    Returns:
        Selected Course object, or None if no courses available or user cancels
    """
    courses = discover_courses(lessons_dir)

    if not courses:
        print("No courses found in the lessons directory.")
        return None

    print("\n" + "=" * 50)
    print("  Available Courses")
    print("=" * 50)

    for i, course in enumerate(courses, start=1):
        print(f"  [{i}] {course.display_name}")
        print(f"      {course.lesson_count} lesson(s)")

    print(f"\n  [0] Cancel")
    print("=" * 50)

    while True:
        try:
            choice = input("\nSelect a course (enter number): ").strip()
            if choice == "0":
                return None

            index = int(choice) - 1
            if 0 <= index < len(courses):
                selected = courses[index]
                print(f"\nSelected: {selected.display_name}")
                return selected
            else:
                print(f"Please enter a number between 0 and {len(courses)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nCancelled")
            return None


def get_course_lesson_files(course: Course) -> List[Path]:
    """Get all lesson file paths for a course.

    Args:
        course: Course object

    Returns:
        List of paths to lesson files in the course
    """
    return course.lesson_files
