from __future__ import annotations

from db_init import get_db_connection
from db_feedback import save_feedback as persist_feedback


def save_chat(
    question: str,
    answer: str,
    latency_ms: float,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    model: str = "",
    judge: dict[str, object] | None = None,
    judge_input_tokens: int = 0,
    judge_output_tokens: int = 0,
) -> int:
    if latency_ms < 0:
        raise ValueError("latency_ms cannot be negative")
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts cannot be negative")
    if judge_input_tokens < 0 or judge_output_tokens < 0:
        raise ValueError("judge token counts cannot be negative")
    if estimated_cost_usd < 0:
        raise ValueError("estimated_cost_usd cannot be negative")
    judge = judge or {}
    judge_scores = [
        judge.get(field)
        for field in ("correctness", "groundedness", "relevance")
    ]
    if any(score is not None and (type(score) is not int or not 1 <= score <= 5) for score in judge_scores):
        raise ValueError("judge scores must be integers between 1 and 5")
    judge_explanation = judge.get("explanation")
    if judge_explanation is not None and not isinstance(judge_explanation, str):
        raise TypeError("judge explanation must be a string")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_logs (
                    question, answer, latency_ms, input_tokens,
                    output_tokens, estimated_cost_usd, model,
                    judge_correctness, judge_groundedness, judge_relevance,
                    judge_explanation, judge_input_tokens,
                    judge_output_tokens, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (
                    question,
                    answer,
                    latency_ms,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    model,
                    judge.get("correctness"),
                    judge.get("groundedness"),
                    judge.get("relevance"),
                    judge_explanation,
                    judge_input_tokens,
                    judge_output_tokens,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("The database did not return the new chat ID")
            return row[0]


def save_feedback(chat_id: int, helpful: bool) -> None:
    persist_feedback(chat_id, helpful)
