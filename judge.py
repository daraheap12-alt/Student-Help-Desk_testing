from __future__ import annotations

import argparse
import json
from typing import Any
from typing import Any

from openai import OpenAI

from assistant import answer_question, create_assistant
from ingest import load_faq_data
from llm_config import create_llm_client, get_llm_model


SCORE_FIELDS = ("correctness", "groundedness", "relevance")


def judge_answer(
    *,
    question: str,
    reference_answer: str,
    generated_answer: str,
    model: str | None = None,
    client: OpenAI | None = None,
) -> dict[str, Any]:
    """Use an LLM to score an answer against a trusted FAQ answer."""
    if client is None:
        client, configured_model = create_llm_client(required=True)
    else:
        configured_model = get_llm_model()
    model = model or configured_model

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Evaluate the assistant answer against the reference answer. "
                    "Score correctness, groundedness, and relevance from 1 (poor) "
                    "to 5 (excellent). Do not reward unsupported claims. Return one "
                    "JSON object with integer fields correctness, groundedness, "
                    "relevance, and a concise string field explanation."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "reference_answer": reference_answer,
                        "assistant_answer": generated_answer,
                    }
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("The judge returned an empty response")
    result = json.loads(content)

    for field in SCORE_FIELDS:
        score = result.get(field)
        if type(score) is not int or not 1 <= score <= 5:
            raise ValueError(f"Judge returned an invalid {field} score")
    if not isinstance(result.get("explanation"), str):
        raise ValueError("Judge response is missing an explanation")

    usage = response.usage
    return {
        **result,
        "model": model,
        "usage": (
            {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            if usage is not None
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Judge one assistant answer against an FAQ.")
    parser.add_argument("--faq-id", required=True, help="Reference FAQ ID, such as faq-067")
    parser.add_argument("--query", help="Question to ask; defaults to the FAQ question")
    parser.add_argument("--model", help="Override the model configured for the selected provider")
    args = parser.parse_args()

    reference = next(
        (doc for doc in load_faq_data() if str(doc.get("id")) == args.faq_id),
        None,
    )
    if reference is None:
        parser.error(f"FAQ ID not found: {args.faq_id}")

    query = args.query or str(reference["question"])
    assistant = create_assistant()
    generated_answer = answer_question(query, assistant=assistant)["answer"]
    result = judge_answer(
        question=query,
        reference_answer=str(reference["answer"]),
        generated_answer=str(generated_answer),
        model=args.model,
    )

    print(json.dumps({"faq_id": args.faq_id, "query": query, **result}, indent=2))


if __name__ == "__main__":
    main()