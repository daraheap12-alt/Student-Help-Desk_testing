from __future__ import annotations

import html
import os
import time

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from assistant import answer_question, create_assistant
from config_utils import get_config_value
from db_init import database_is_configured
from db_query import (
    query_dashboard_summary,
    query_feedback_summary,
    query_judge_summary,
    query_recent_logs,
)
from db_save import save_chat, save_feedback
from judge import judge_answer

load_dotenv()

st.set_page_config(
    page_title="Student Help Desk",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #202b3a;
        --muted: #718096;
        --accent: #315f9b;
        --canvas: #f6f8fb;
        --sidebar: #20252d;
    }

    .stApp {
        background: var(--canvas);
        color: var(--ink);
    }

    [data-testid="stAppViewContainer"] {
        background: var(--canvas);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 5rem;
    }

    [data-testid="stSidebar"] {
        background: var(--sidebar);
        border-right: 1px solid #303742;
        width: 16rem !important;
        min-width: 16rem !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #e4e9f0;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stSidebar"] label {
        color: #e4e9f0;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] small {
        color: #aab4c2;
    }

    [data-testid="stAppViewContainer"] [data-testid="stAppViewBlockContainer"] h1 {
        color: var(--ink);
        letter-spacing: -0.035em;
        font-weight: 700;
        font-size: clamp(1.65rem, 2.6vw, 2rem);
        line-height: 1.15;
    }

    .app-brand {
        padding: 0.4rem 0 1.1rem;
        margin-bottom: 1.2rem;
        border-bottom: 1px solid #3a414b;
    }

    .app-brand-title {
        color: #f7f9fc;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .app-brand-caption {
        color: #aab4c2;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }

    .topic-list {
        display: grid;
        gap: 0.35rem;
        margin: 0.4rem 0 1.25rem;
    }

    .topic-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        min-height: 2.5rem;
        padding: 0.35rem 0.55rem;
        border: 1px solid transparent;
        border-radius: 10px;
        color: #e4e9f0;
        font-size: 0.9rem;
        line-height: 1.25;
        transition: background-color 120ms ease, border-color 120ms ease;
    }

    .topic-row:hover {
        background: #2b323d;
        border-color: #3a4552;
    }

    .topic-icon {
        display: inline-flex;
        flex: 0 0 1.8rem;
        align-items: center;
        justify-content: center;
        width: 1.8rem;
        height: 1.8rem;
        border-radius: 8px;
        background: #343e4b;
        font-size: 1rem;
    }

    .page-eyebrow {
        color: var(--accent);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 0.35rem;
    }

    [data-testid="stChatMessage"] {
        background: #fff;
        border: 1px solid #e7ebf0;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 18px rgba(32, 43, 58, 0.035);
    }

    [data-testid="stChatInput"] {
        background: #fff;
        border: 1px solid #dfe5ec;
        border-radius: 16px;
        box-shadow: 0 8px 28px rgba(32, 43, 58, 0.08);
    }

    [data-testid="stChatInput"] textarea {
        color: var(--ink);
    }

    .stButton > button {
        border-radius: 10px;
        border-color: #dce3eb;
        color: var(--ink);
        font-weight: 600;
        transition: border-color 120ms ease, background-color 120ms ease;
    }

    .stButton > button:hover {
        border-color: #9bb4d3;
        color: var(--accent);
    }

    [data-testid="stMetric"] {
        background: #fff;
        border: 1px solid #e7ebf0;
        border-radius: 14px;
        padding: 1rem;
    }

    @media (max-width: 700px) {
        [data-testid="stMainBlockContainer"] {
            padding: 1rem 1rem 4rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

TOPICS = [
    "Enrollment",
    "Course Access",
    "Technical Issues",
    "Billing",
    "Deadlines",
    "Certificates",
    "Student Records",
    "General Support",
]

DEFAULT_INPUT_PRICE = 0.0
DEFAULT_OUTPUT_PRICE = 0.0

TOPIC_ICONS = {
    "Admissions and Enrollment": "🎓",
    "Certificates and Completion": "🏅",
    "Course Access": "📚",
    "Deadlines and Extensions": "📅",
    "General Support": "💬",
    "Payments and Billing": "💳",
    "Student Records": "🗂️",
    "Technical Support": "🛠️",
}


if "history" not in st.session_state:
    st.session_state.history = []

if "input_price_per_million" not in st.session_state:
    st.session_state.input_price_per_million = float(
        get_config_value("INPUT_TOKEN_PRICE", str(DEFAULT_INPUT_PRICE))
    )

if "output_price_per_million" not in st.session_state:
    st.session_state.output_price_per_million = float(
        get_config_value("OUTPUT_TOKEN_PRICE", str(DEFAULT_OUTPUT_PRICE))
    )

if "last_qa" not in st.session_state:
    st.session_state.last_qa = None


@st.cache_resource
def get_assistant():
    assistant = create_assistant()
    assistant.input_price_per_million = st.session_state.input_price_per_million
    assistant.output_price_per_million = st.session_state.output_price_per_million
    return assistant


def chat_page():
    header_col1, header_col2, header_col3 = st.columns([5, 1.35, 1])

    with header_col1:
        st.markdown('<div class="page-eyebrow">Student support · Live chat</div>', unsafe_allow_html=True)
        st.title("Student Help Desk Assistant")
        st.caption(
            "Ask about enrollment, course access, technical issues, billing, deadlines, certificates, or student records."
        )

    with header_col2:
        st.write("")
        if st.button("📊 View Dashboard", use_container_width=True):
            st.switch_page(page_dashboard)

    with header_col3:
        st.write("")
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page(page_settings)

    assistant = get_assistant()

    sections = sorted(
        {
            str(document.get("section", "General Support"))
            for document in getattr(assistant, "index", [])
        }
    )

    with st.sidebar:
        st.markdown(
            """
            <div class="app-brand">
                <div class="app-brand-title">🎓 Student Help Desk</div>
                <div class="app-brand-caption">STUDENT SUPPORT · BETA</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.subheader("Help topics")
        st.caption(f"{len(getattr(assistant, 'index', []))} questions in the local dataset")
        topic_rows = [
            (
                '<div class="topic-row">'
                f'<span class="topic-icon" role="img" aria-label="">'
                f'{html.escape(TOPIC_ICONS.get(section, "📌"))}</span>'
                f'<span>{html.escape(section)}</span></div>'
            )
            for section in sections
        ]
        st.markdown(
            '<div class="topic-list">' + "".join(topic_rows) + "</div>",
            unsafe_allow_html=True,
        )

        st.subheader("Token pricing (USD / 1M)")
        st.number_input(
            "Input price",
            min_value=0.0,
            step=0.01,
            format="%.4f",
            key="input_price_per_million",
        )
        st.number_input(
            "Output price",
            min_value=0.0,
            step=0.01,
            format="%.4f",
            key="output_price_per_million",
        )

    for role, content in st.session_state.history:
        with st.chat_message(role):
            st.markdown(content)

    prompt = st.chat_input("Describe your student support question")

    if prompt:
        st.session_state.history.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        started = time.time()
        try:
            result = answer_question(prompt, assistant=assistant)
        except Exception as exc:
            st.error(f"Something went wrong while answering your question: {exc}")
            st.session_state.history.append(("assistant", "Sorry, I couldn't answer that right now."))
            with st.chat_message("assistant"):
                st.markdown("Sorry, I couldn't answer that right now.")
            st.stop()

        elapsed_ms = round((time.time() - started) * 1000, 2)
        answer = result.get("answer", "I couldn't generate a response.")
        latency_ms = float(result.get("latency_ms", elapsed_ms))
        usage = result.get("usage") or {}
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        generation_cost_usd = (
            input_tokens * st.session_state.input_price_per_million
            + output_tokens * st.session_state.output_price_per_million
        ) / 1_000_000

        retrieved_documents = result.get("retrieved_documents", [])
        reference_answer = "\n\n".join(
            (
                f"Section: {document.get('section', 'General Support')}\n"
                f"Question: {document.get('question', '')}\n"
                f"Answer: {document.get('answer', '')}"
            )
            for document in retrieved_documents
        )
        judge_result = None
        judge_error = None
        if reference_answer:
            try:
                judge_result = judge_answer(
                    question=prompt,
                    reference_answer=reference_answer,
                    generated_answer=answer,
                    model=str(result.get("model") or assistant.model),
                )
            except Exception as exc:
                judge_error = str(exc)
        else:
            judge_error = "No supporting FAQ context was retrieved."

        judge_usage = (judge_result or {}).get("usage") or {}
        judge_input_tokens = int(judge_usage.get("input_tokens", 0))
        judge_output_tokens = int(judge_usage.get("output_tokens", 0))
        judge_cost_usd = (
            judge_input_tokens * st.session_state.input_price_per_million
            + judge_output_tokens * st.session_state.output_price_per_million
        ) / 1_000_000
        estimated_cost_usd = generation_cost_usd + judge_cost_usd

        chat_id = None
        persistence_error = None
        if database_is_configured():
            try:
                chat_id = save_chat(
                    prompt,
                    answer,
                    latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=estimated_cost_usd,
                    model=str(result.get("model") or ""),
                    judge=judge_result,
                    judge_input_tokens=judge_input_tokens,
                    judge_output_tokens=judge_output_tokens,
                )
            except Exception as exc:
                persistence_error = str(exc)
        else:
            persistence_error = "DATABASE_URL is not set; this conversation was not saved."

        st.session_state.last_qa = {
            "question": prompt,
            "answer": answer,
            "usage": usage,
            "retrieved_documents": retrieved_documents,
            "elapsed_ms": latency_ms,
            "input_price_per_million": st.session_state.input_price_per_million,
            "output_price_per_million": st.session_state.output_price_per_million,
            "estimated_cost_usd": estimated_cost_usd,
            "judge": judge_result,
            "judge_error": judge_error,
            "chat_id": chat_id,
            "persistence_error": persistence_error,
            "feedback": None,
        }

        with st.chat_message("assistant"):
            st.markdown(answer)
            st.caption(f"Response time: {latency_ms:.2f} ms")
            if persistence_error:
                st.warning(f"Monitoring record was not saved: {persistence_error}")

            if judge_result:
                relevance = int(judge_result["relevance"])
                verdict, color = (
                    ("RELEVANT", "🟢")
                    if relevance >= 4
                    else ("PARTLY RELEVANT", "🟡")
                    if relevance == 3
                    else ("NON RELEVANT", "🔴")
                )
                with st.expander(
                    f"⚖️ LLM Judge Evaluation: {color} {verdict}",
                    expanded=True,
                ):
                    score_columns = st.columns(3)
                    score_columns[0].metric(
                        "Correctness",
                        f"{judge_result['correctness']}/5",
                    )
                    score_columns[1].metric(
                        "Groundedness",
                        f"{judge_result['groundedness']}/5",
                    )
                    score_columns[2].metric(
                        "Relevance",
                        f"{judge_result['relevance']}/5",
                    )
                    st.write(f"**Explanation:** {judge_result['explanation']}")
                    st.caption(
                        f"Judge model: {judge_result['model']} | "
                        f"Estimated judge cost: ${judge_cost_usd:.6f}"
                    )
            elif judge_error:
                st.warning(f"LLM judge evaluation unavailable: {judge_error}")

            usage = st.session_state.last_qa["usage"]
            input_tokens = int(usage.get("input_tokens", 0))
            output_tokens = int(usage.get("output_tokens", 0))

            if input_tokens or output_tokens:
                input_cost = input_tokens * st.session_state.input_price_per_million / 1_000_000
                output_cost = output_tokens * st.session_state.output_price_per_million / 1_000_000

                col1, col2 = st.columns(2)
                col1.metric("Input cost", f"${input_cost:.6f}")
                col2.metric("Output cost", f"${output_cost:.6f}")

                st.caption(
                    f"{input_tokens:,} input tokens at "
                    f"${st.session_state.input_price_per_million:.4f}/1M | "
                    f"{output_tokens:,} output tokens at "
                    f"${st.session_state.output_price_per_million:.4f}/1M"
                )
            else:
                st.caption("Token usage unavailable for this response.")

            with st.expander("Retrieved context", expanded=False):
                docs = st.session_state.last_qa["retrieved_documents"]
                if not docs:
                    st.info("No supporting documents were retrieved for this query.")
                for doc in docs:
                    st.markdown(f"**Section:** {doc.get('section', 'General Support')}")
                    st.markdown(f"**Question:** {doc.get('question', '')}")
                    st.markdown(f"**Answer:** {doc.get('answer', '')}")
                    st.markdown("---")

        st.session_state.history.append(("assistant", answer))

    if st.session_state.last_qa:
        st.markdown("---")
        with st.chat_message("assistant"):
            st.markdown("Last answer summary")
            st.caption(
                f"Question: {st.session_state.last_qa['question']} | "
                f"Response time: {st.session_state.last_qa['elapsed_ms']} ms"
            )
        chat_id = st.session_state.last_qa["chat_id"]
        feedback = st.session_state.last_qa["feedback"]
        if chat_id is not None and feedback is None:
            st.markdown("##### Was this answer helpful?")
            feedback_col1, feedback_col2 = st.columns(2)
            with feedback_col1:
                if st.button("👍 Helpful", key=f"feedback_helpful_{chat_id}"):
                    try:
                        save_feedback(chat_id, True)
                        st.session_state.last_qa["feedback"] = True
                        feedback = True
                    except Exception as exc:
                        st.error(f"Unable to save feedback: {exc}")
            with feedback_col2:
                if st.button("👎 Not helpful", key=f"feedback_unhelpful_{chat_id}"):
                    try:
                        save_feedback(chat_id, False)
                        st.session_state.last_qa["feedback"] = False
                        feedback = False
                    except Exception as exc:
                        st.error(f"Unable to save feedback: {exc}")
        if feedback is True:
            st.success("Thanks for your feedback.")
        elif feedback is False:
            st.success("Thanks for your feedback.")


def dashboard_page():
    header_col1, header_col2, header_col3 = st.columns([3, 1, 1])

    with header_col1:
        st.title("Student Help Desk Dashboard")

    with header_col2:
        st.write("")
        if st.button("💬 Back to Chat", use_container_width=True):
            st.switch_page(page_chat)

    with header_col3:
        st.write("")
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page(page_settings)

    st.subheader("Overview")
    if not database_is_configured():
        st.info("Configure DATABASE_URL or POSTGRES_HOST to enable persistent monitoring metrics.")
        return

    try:
        total, avg_latency, p95_latency, total_cost = query_dashboard_summary()
        feedback_total, helpful_total = query_feedback_summary()
        judged_total, avg_correctness, avg_groundedness, avg_relevance = query_judge_summary()
        rows = query_recent_logs(limit=50)
    except Exception as exc:
        st.error(f"Unable to load monitoring data: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total queries", total or 0)
    col2.metric("Average response time", f"{(avg_latency or 0):.0f} ms")
    col3.metric("P95 response time", f"{(p95_latency or 0):.0f} ms")
    col4.metric("Estimated cost", f"${(total_cost or 0):.6f}")

    feedback_rate = helpful_total / feedback_total if feedback_total else 0.0
    feedback_col1, feedback_col2 = st.columns(2)
    feedback_col1.metric("Feedback responses", feedback_total or 0)
    feedback_col2.metric("Helpful rate", f"{feedback_rate:.0%}")

    st.subheader("LLM judge evaluation")
    judge_columns = st.columns(4)
    judge_columns[0].metric("Evaluated answers", judged_total or 0)
    judge_columns[1].metric("Avg correctness", f"{(avg_correctness or 0):.1f}/5")
    judge_columns[2].metric("Avg groundedness", f"{(avg_groundedness or 0):.1f}/5")
    judge_columns[3].metric("Avg relevance", f"{(avg_relevance or 0):.1f}/5")

    st.subheader("Recent requests")
    if not rows:
        st.info("No conversations have been recorded yet.")
        return

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
    st.dataframe(df, use_container_width=True, hide_index=True)

    chart_df = df.sort_values("created_at")
    st.subheader("Response time over time")
    st.line_chart(chart_df, x="created_at", y="latency_ms")
    st.subheader("Estimated cost over time")
    st.line_chart(chart_df, x="created_at", y="estimated_cost_usd")


def settings_page():
    header_col1, header_col2 = st.columns([4, 1])

    with header_col1:
        st.title("⚙️ LLM & API Settings")

    with header_col2:
        st.write("")
        if st.button("💬 Back to Chat", use_container_width=True):
            st.switch_page(page_chat)

    st.markdown(
        "Configure your LLM model and API credentials here. These settings are dynamically applied to the Student Help Desk Assistant without restarting the application."
    )

    with st.form("settings_form"):
        st.subheader("API configuration")
        api_key_input = st.text_input(
            "API Key",
            value=get_config_value("OPENAI_API_KEY", ""),
            type="password",
            help="Your model API key",
        )

        model_input = st.text_input(
            "Model Name",
            value=get_config_value("LLM_MODEL", "qwen3.7-max-2026-06-08"),
            help="Example: qwen3.7-max-2026-06-08, qwen-plus, qwen-turbo",
        )

        base_url_input = st.text_input(
            "Base URL",
            value=get_config_value(
                "OPENAI_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
            help="Default compatible model endpoint",
        )

        st.subheader("Token pricing")
        input_price_input = st.number_input(
            "Input token price ($ / 1M)",
            min_value=0.0,
            value=float(st.session_state.input_price_per_million),
            step=0.01,
            format="%.4f",
        )
        output_price_input = st.number_input(
            "Output token price ($ / 1M)",
            min_value=0.0,
            value=float(st.session_state.output_price_per_million),
            step=0.01,
            format="%.4f",
        )

        submitted = st.form_submit_button("💾 Save Settings", use_container_width=True)
        if submitted:
            os.environ["OPENAI_API_KEY"] = api_key_input.strip()
            os.environ["LLM_MODEL"] = model_input.strip()
            os.environ["OPENAI_BASE_URL"] = base_url_input.strip()
            os.environ["INPUT_TOKEN_PRICE"] = str(input_price_input)
            os.environ["OUTPUT_TOKEN_PRICE"] = str(output_price_input)

            st.session_state.input_price_per_million = float(input_price_input)
            st.session_state.output_price_per_million = float(output_price_input)

            st.cache_resource.clear()
            st.success("✅ Settings updated successfully!")

    st.subheader("Quick Model Presets")
    st.caption("Click to load default model name and pricing presets:")
    preset_cols = st.columns(4)
    presets = {
        "qwen3.7-max-2026-06-08": {"input": 0.96, "output": 3.84},
        "qwen-plus": {"input": 0.40, "output": 1.20},
        "qwen-turbo": {"input": 0.05, "output": 0.20},
        "qwen-max": {"input": 1.60, "output": 6.40},
    }

    for i, (model_name, pricing) in enumerate(presets.items()):
        with preset_cols[i]:
            label = f"**{model_name.split('-202')[0]}**\n\n`${pricing['input']:.2f}` / `${pricing['output']:.2f}`"
            if st.button(label, use_container_width=True, key=f"preset_{i}"):
                os.environ["LLM_MODEL"] = model_name
                os.environ["INPUT_TOKEN_PRICE"] = str(pricing["input"])
                os.environ["OUTPUT_TOKEN_PRICE"] = str(pricing["output"])
                st.session_state.input_price_per_million = float(pricing["input"])
                st.session_state.output_price_per_million = float(pricing["output"])
                st.cache_resource.clear()
                st.rerun()


page_chat = st.Page(chat_page, title="Chat", icon="💬", default=True)
page_dashboard = st.Page(dashboard_page, title="Dashboard", icon="📊", url_path="dashboard")
page_settings = st.Page(settings_page, title="Settings", icon="⚙️", url_path="settings")

pg = st.navigation([page_chat, page_dashboard, page_settings])
pg.run()