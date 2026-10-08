from __future__ import annotations

import argparse
from typing import Any

from assistant import create_assistant
from rag_helper import RAGBase


def evaluate_retrieval(
    assistant: RAGBase,
    test_cases: list[dict[str, Any]] | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    """Measure whether expected FAQ records appear in the retrieved results."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if test_cases is None:
        test_cases = [
            {"query": str(doc["question"]), "relevant_ids": [str(doc["id"])]}
            for doc in assistant.index
            if doc.get("question") and doc.get("id")
        ]

    if not test_cases:
        raise ValueError("No evaluation test cases were provided")

    reciprocal_ranks: list[float] = []
    misses: list[str] = []

    for case in test_cases:
        query = str(case["query"])
        relevant_ids = {str(record_id) for record_id in case["relevant_ids"]}
        retrieved = assistant.search(query, top_k=top_k)
        rank = next(
            (
                position
                for position, document in enumerate(retrieved, start=1)
                if str(document.get("id", "")) in relevant_ids
            ),
            None,
        )

        if rank is None:
            reciprocal_ranks.append(0.0)
            misses.append(query)
        else:
            reciprocal_ranks.append(1.0 / rank)

    evaluated = len(test_cases)
    return {
        "top_k": top_k,
        "evaluated": evaluated,
        "hit_rate": (evaluated - len(misses)) / evaluated,
        "mrr": sum(reciprocal_ranks) / evaluated,
        "misses": misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate FAQ retrieval quality.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results to check")
    args = parser.parse_args()

    metrics = evaluate_retrieval(create_assistant(), top_k=args.top_k)
    print(f"Questions evaluated: {metrics['evaluated']}")
    print(f"Hit rate@{metrics['top_k']}: {metrics['hit_rate']:.1%}")
    print(f"MRR@{metrics['top_k']}: {metrics['mrr']:.3f}")
    if metrics["misses"]:
        print("Questions with no relevant result in the top-k:")
        for query in metrics["misses"]:
            print(f"- {query}")


if __name__ == "__main__":
    main()