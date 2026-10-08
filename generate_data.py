from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from typing import Any

from db_init import get_db_connection
from ingest import load_faq_data


def generate_mock_data(
    num_rows: int = 25,
    *,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    if num_rows < 0:
        raise ValueError("num_rows cannot be negative")

    documents = load_faq_data()
    if num_rows and not documents:
        raise ValueError("Cannot generate monitoring data without FAQ records")

    rng = random.Random(seed)
    base_time = datetime.now().astimezone().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ) - timedelta(days=1)
    rows: list[dict[str, Any]] = []

    for index in range(num_rows):
        document = documents[index % len(documents)]
        created_at = (base_time + timedelta(minutes=index * 8)).isoformat()
        rows.append(
            {
                "created_at": created_at,
                "latency_ms": round(rng.uniform(120.0, 2600.0), 2),
                "question": document["question"],
                "answer": document["answer"],
                "input_tokens": rng.randint(40, 300),
                "output_tokens": rng.randint(20, 250),
                "estimated_cost_usd": round(rng.uniform(0.0001, 0.01), 6),
                "model": "synthetic",
                "helpful": rng.choice([True, False]),
            }
        )

    return rows


def insert_mock_data(num_rows: int = 25, *, seed: int | None = None) -> int:
    rows = generate_mock_data(num_rows, seed=seed)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO chat_logs (
                        question, answer, latency_ms, input_tokens,
                        output_tokens, estimated_cost_usd, model, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        row["question"],
                        row["answer"],
                        row["latency_ms"],
                        row["input_tokens"],
                        row["output_tokens"],
                        row["estimated_cost_usd"],
                        row["model"],
                        row["created_at"],
                    ),
                )
                inserted = cur.fetchone()
                if inserted is None:
                    raise RuntimeError("The database did not return a synthetic chat ID")
                cur.execute(
                    """
                    INSERT INTO feedback (chat_id, helpful, created_at)
                    VALUES (%s, %s, %s)
                    """,
                    (inserted[0], row["helpful"], row["created_at"]),
                )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert synthetic monitoring data.")
    parser.add_argument("--count", type=int, default=25, help="Number of records to create")
    parser.add_argument("--seed", type=int, help="Optional seed for repeatable data")
    args = parser.parse_args()
    inserted = insert_mock_data(args.count, seed=args.seed)
    print(f"Inserted {inserted} synthetic conversations and feedback records.")


if __name__ == "__main__":
    main()
