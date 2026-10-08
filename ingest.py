from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_faq_data(data_path: str | Path = "student_help_desk.json") -> list[dict[str, Any]]:
    """Load the local course help-desk FAQ dataset."""
    file_path = Path(data_path)
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as fp:
        rows = json.load(fp)

    if isinstance(rows, dict):
        rows = rows.get("items", [rows])

    if not isinstance(rows, list):
        raise ValueError("FAQ dataset must contain a list of records")

    documents: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"FAQ record {index + 1} must be an object")

        record_id = str(row.get("id", index)).strip()
        question = str(row.get("question", "")).strip()
        answer = str(row.get("answer", "")).strip()
        section = str(row.get("section", "")).strip()
        if not question or not answer or not section:
            raise ValueError(f"FAQ record {record_id} is missing question, answer, or section")
        if record_id in seen_ids:
            raise ValueError(f"Duplicate FAQ record ID: {record_id}")
        seen_ids.add(record_id)

        documents.append(
            {
                "id": record_id,
                "course": row.get("course", "student-help-desk"),
                "section": section,
                "question": question,
                "answer": answer,
                "text": f"{question} {answer}".strip(),
            }
        )

    return documents


def build_index(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the searchable document list used by the RAG assistant."""
    return documents
