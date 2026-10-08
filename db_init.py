from __future__ import annotations

from dotenv import load_dotenv

from config_utils import get_config_value


def get_db_connection():
    load_dotenv()

    import psycopg

    database_url = get_config_value("DATABASE_URL")
    if database_url:
        return psycopg.connect(database_url)

    host = get_config_value("POSTGRES_HOST")
    if not host:
        raise ValueError("Set DATABASE_URL or POSTGRES_HOST to enable PostgreSQL")

    return psycopg.connect(
        host=host,
        dbname=get_config_value("POSTGRES_DB", "student_help_desk"),
        user=get_config_value("POSTGRES_USER", "student_help_desk"),
        password=get_config_value("POSTGRES_PASSWORD", ""),
    )


def database_is_configured() -> bool:
    load_dotenv()
    return bool(get_config_value("DATABASE_URL") or get_config_value("POSTGRES_HOST"))


def init_db() -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    latency_ms DOUBLE PRECISION NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
                    model TEXT NOT NULL DEFAULT '',
                    judge_correctness SMALLINT,
                    judge_groundedness SMALLINT,
                    judge_relevance SMALLINT,
                    judge_explanation TEXT,
                    judge_input_tokens INTEGER NOT NULL DEFAULT 0,
                    judge_output_tokens INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE chat_logs
                    ADD COLUMN IF NOT EXISTS input_tokens INTEGER NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS output_tokens INTEGER NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS estimated_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS judge_correctness SMALLINT,
                    ADD COLUMN IF NOT EXISTS judge_groundedness SMALLINT,
                    ADD COLUMN IF NOT EXISTS judge_relevance SMALLINT,
                    ADD COLUMN IF NOT EXISTS judge_explanation TEXT,
                    ADD COLUMN IF NOT EXISTS judge_input_tokens INTEGER NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS judge_output_tokens INTEGER NOT NULL DEFAULT 0
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    chat_id INTEGER NOT NULL REFERENCES chat_logs(id),
                    helpful BOOLEAN NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


if __name__ == "__main__":
    init_db()
    print("Database initialized")
