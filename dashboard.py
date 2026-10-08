from __future__ import annotations

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from db_init import database_is_configured
from db_query import (
    query_dashboard_summary,
    query_feedback_summary,
    query_judge_summary,
    query_recent_logs,
)
from ingest import load_faq_data


load_dotenv()

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊")
st.title("RAG Monitoring Dashboard")

documents = load_faq_data()
sections = sorted({document.get("section", "General Support") for document in documents})

st.subheader("Current knowledge base")
dataset_columns = st.columns(2)
dataset_columns[0].metric("FAQ records", len(documents))
dataset_columns[1].metric("Support sections", len(sections))
st.caption("Sections: " + ", ".join(sections))

if not database_is_configured():
    st.info("Configure DATABASE_URL or POSTGRES_HOST to enable live request metrics.")
    st.stop()

try:
    total, avg_latency, p95_latency, total_cost = query_dashboard_summary()
    feedback_total, helpful_total = query_feedback_summary()
    judged_total, avg_correctness, avg_groundedness, avg_relevance = query_judge_summary()
    rows = query_recent_logs(limit=50)
except Exception as exc:
    st.error(f"Unable to load metrics: {exc}")
    st.stop()

metric_columns = st.columns(4)
metric_columns[0].metric("Total requests", total or 0)
metric_columns[1].metric("Average latency (ms)", round(avg_latency or 0, 2))
metric_columns[2].metric("P95 latency (ms)", round(p95_latency or 0, 2))
metric_columns[3].metric("Estimated cost (USD)", f"${(total_cost or 0):.6f}")

helpful_rate = helpful_total / feedback_total if feedback_total else 0.0
feedback_columns = st.columns(2)
feedback_columns[0].metric("Feedback responses", feedback_total or 0)
feedback_columns[1].metric("Helpful rate", f"{helpful_rate:.0%}")

st.subheader("LLM judge evaluation")
judge_columns = st.columns(4)
judge_columns[0].metric("Evaluated answers", judged_total or 0)
judge_columns[1].metric("Average correctness", f"{(avg_correctness or 0):.1f}/5")
judge_columns[2].metric("Average groundedness", f"{(avg_groundedness or 0):.1f}/5")
judge_columns[3].metric("Average relevance", f"{(avg_relevance or 0):.1f}/5")

columns = [
    "id",
    "question",
    "answer",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
    "model",
    "judge_correctness",
    "judge_groundedness",
    "judge_relevance",
    "judge_explanation",
    "judge_input_tokens",
    "judge_output_tokens",
    "created_at",
]
df = pd.DataFrame(rows, columns=columns)
st.subheader("Recent requests")
if df.empty:
    st.info("No conversations have been recorded yet.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
    chart_df = df.sort_values("created_at")
    st.subheader("Latency over time")
    st.line_chart(chart_df, x="created_at", y="latency_ms")
    st.subheader("Cost over time")
    st.line_chart(chart_df, x="created_at", y="estimated_cost_usd")
