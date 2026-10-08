from __future__ import annotations

from db_init import get_db_connection


def save_feedback(chat_id: int, helpful: bool) -> None:
    """Save a thumbs-up or thumbs-down rating for a recorded chat request."""
    if chat_id <= 0:
        raise ValueError("chat_id must be a positive database ID")
    if not isinstance(helpful, bool):
        raise TypeError("helpful must be a boolean")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (chat_id, helpful, created_at) VALUES (%s, %s, NOW())",
                (chat_id, helpful),
            )
        conn.commit()
