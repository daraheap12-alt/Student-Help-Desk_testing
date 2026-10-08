from __future__ import annotations

import re
from typing import Any

from openai import OpenAI

from llm_config import create_llm_client, get_llm_model


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def search_documents(index: list[dict[str, Any]], query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Simple keyword-based retrieval for the local JSON dataset."""
    if not index:
        return []

    query_tokens = set(normalize_text(query).split())
    if not query_tokens:
        return index[:top_k]

    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in index:
        text = " ".join(
            [
                str(doc.get("question", "")),
                str(doc.get("answer", "")),
                str(doc.get("section", "")),
            ]
        )
        normalized = normalize_text(text)
        doc_tokens = set(normalized.split())

        overlap = len(query_tokens & doc_tokens)
        direct_match = 1 if query.lower() in str(doc.get("question", "")).lower() else 0
        section_match = 1 if query_tokens & set(normalize_text(str(doc.get("section", "")).lower()).split()) else 0
        score = overlap * 3 + direct_match * 5 + section_match * 2

        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


class RAGBase:
    def __init__(
        self,
        index: list[dict[str, Any]],
        llm_client: OpenAI | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ):
        self.index = index
        if llm_client is None:
            self.llm_client, configured_model = create_llm_client()
        else:
            self.llm_client = llm_client
            configured_model = get_llm_model()
        self.model = model or configured_model
        self.system_prompt = system_prompt or (
            "You are a helpful student support assistant. Answer using the course help-desk context "
            "provided by the user. Be concise, accurate, and practical."
        )
        self.last_usage: dict[str, int] | None = None

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        return search_documents(self.index, query, top_k=top_k)

    def _build_prompt(self, query: str, documents: list[dict[str, Any]]) -> str:
        context_parts = []
        for doc in documents:
            section = doc.get("section", "General")
            question = doc.get("question", "")
            answer = doc.get("answer", "")
            context_parts.append(f"Section: {section}\nQuestion: {question}\nAnswer: {answer}")

        context_text = "\n\n---\n\n".join(context_parts)
        return (
            "Use only the context below to answer the user's question. "
            "If the answer is unclear, tell them to check the official course page or contact the provider.\n\n"
            f"Question: {query}\n\nContext:\n{context_text}"
        )

    def rag(
        self,
        query: str,
        top_k: int = 3,
        documents: list[dict[str, Any]] | None = None,
    ) -> str:
        self.last_usage = None
        if documents is None:
            documents = self.search(query, top_k=top_k)
        if not documents:
            return "I could not find a relevant answer in the local help-desk dataset."

        if self.llm_client is None:
            return documents[0].get("answer", "")

        prompt = self._build_prompt(query, documents)

        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        if response.usage is not None:
            self.last_usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("The model returned an empty answer")
        return content
