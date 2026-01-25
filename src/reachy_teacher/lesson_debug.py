"""Debug script to verify lesson content is loaded correctly."""
from __future__ import annotations

from pathlib import Path
from .document_loader import (
    load_document,
    discover_courses,
    select_course_interactive,
)


def main():
    print("=" * 60)
    print("LESSON CONTENT DEBUG")
    print("=" * 60)

    # Discover courses
    courses = discover_courses("lessons")
    if not courses:
        print("No courses found in lessons/")
        return

    print(f"\nFound {len(courses)} course(s):\n")

    for course in courses:
        print(f"Course: {course.display_name}")
        print(f"  Path: {course.path}")
        print(f"  Lessons: {course.lesson_count}")

        for i, lesson_file in enumerate(course.lesson_files, 1):
            print(f"\n  [{i}] {lesson_file.name}")
            print(f"      Full path: {lesson_file}")

            # Load and show preview
            try:
                docs = load_document(lesson_file)
                total_chars = sum(len(d.page_content) for d in docs)
                print(f"      Loaded: {len(docs)} document(s), {total_chars} total characters")

                # Show first 500 chars of content
                if docs:
                    preview = docs[0].page_content[:500].replace("\n", " ").strip()
                    print(f"      Preview: {preview}...")
            except Exception as e:
                print(f"      ERROR loading: {e}")

        print()

    # Interactive: select and show full content
    print("\n" + "=" * 60)
    print("SELECT A LESSON TO VIEW FULL CONTENT")
    print("=" * 60)

    course = select_course_interactive("lessons")
    if not course:
        return

    print(f"\nLessons in {course.display_name}:")
    for i, f in enumerate(course.lesson_files, 1):
        print(f"  [{i}] {f.name}")

    print(f"  [0] Cancel")

    while True:
        try:
            choice = input("\nSelect lesson number: ").strip()
            if choice == "0":
                return

            idx = int(choice) - 1
            if 0 <= idx < len(course.lesson_files):
                break
            print(f"Enter 0-{len(course.lesson_files)}")
        except ValueError:
            print("Enter a number")

    lesson_file = course.lesson_files[idx]
    print(f"\n{'=' * 60}")
    print(f"FULL CONTENT: {lesson_file.name}")
    print("=" * 60)

    docs = load_document(lesson_file)
    for i, doc in enumerate(docs):
        print(f"\n--- Document {i + 1} ---")
        print(doc.page_content)
        print(f"\nMetadata: {doc.metadata}")


if __name__ == "__main__":
    main()
