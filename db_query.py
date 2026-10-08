from __future__ import annotations

from db_init import get_db_connection


def query_recent_logs(limit: int = 20):
    if type(limit) is not int or limit <= 0:
        raise ValueError("limit must be a positive integer")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, latency_ms, input_tokens,
                       output_tokens, estimated_cost_usd, model,
                       judge_correctness, judge_groundedness, judge_relevance,
                       judge_explanation, judge_input_tokens,
                       judge_output_tokens, created_at
                FROM chat_logs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def query_latency_summary():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT AVG(latency_ms),
                       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)
                FROM chat_logs
                """
            )
            return cur.fetchone()


def query_dashboard_summary():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*), AVG(latency_ms),
                       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms),
                       COALESCE(SUM(estimated_cost_usd), 0)
                FROM chat_logs
                """
            )
            return cur.fetchone()


def query_feedback_summary():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*), COUNT(*) FILTER (WHERE helpful)
                FROM feedback
                """
            )
            return cur.fetchone()


def query_judge_summary():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(judge_relevance),
                       AVG(judge_correctness),
                       AVG(judge_groundedness),
                       AVG(judge_relevance)
                FROM chat_logs
                """
            )
            return cur.fetchone()
