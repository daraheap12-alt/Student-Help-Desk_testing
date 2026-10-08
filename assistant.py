from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ingest import build_index, load_faq_data
from rag_helper import RAGBase


def create_assistant(data_path: str | Path | None = None, model: str | None = None) -> RAGBase:
    """Create a course help-desk assistant backed by the local FAQ dataset.

    This is the component used by the user-facing chat app. It prepares the
    retrieval index and exposes a simple interface for logging metrics, storing
    conversations, and dashboarding real traffic.
    """
    load_dotenv()

    if data_path is None:
        data_path = Path(__file__).resolve().parent / "student_help_desk.json"

    documents = load_faq_data(data_path)
    index = build_index(documents)
    return RAGBase(index=index, model=model)


def answer_question(
    query: str,
    *,
    assistant: RAGBase | None = None,
    top_k: int = 3,
    include_sources: bool = True,
) -> dict[str, Any]:
    """Run a question through the RAG pipeline and return structured output.

    The structured format is intended for downstream monitoring: user app logs,
    database inserts, and Grafana visualizations can all consume the same data.
    """
    started_at = time.time()

    if assistant is None:
        assistant = create_assistant()

    documents = assistant.search(query, top_k=top_k)
    answer = assistant.rag(query, top_k=top_k, documents=documents)
    latency_ms = round((time.time() - started_at) * 1000, 2)

    payload = {
        "query": query,
        "answer": answer,
        "latency_ms": latency_ms,
        "model": assistant.model,
        "usage": assistant.last_usage,
        "dataset_size": len(assistant.index),
        "dataset_sections": sorted(
            {
                str(doc.get("section", "General Support"))
                for doc in assistant.index
            }
        ),
        "retrieved_documents": [
            {
                "section": doc.get("section", "General"),
                "question": doc.get("question", ""),
                "answer": doc.get("answer", ""),
            }
            for doc in documents
        ]
        if include_sources
        else [],
    }

    return payload


if __name__ == "__main__":
    assistant = create_assistant()

    query = "I need to merge two student accounts that were created with different emails."
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])

    result = answer_question(query, assistant=assistant)
    print(json.dumps(result, ensure_ascii=False, indent=2))
