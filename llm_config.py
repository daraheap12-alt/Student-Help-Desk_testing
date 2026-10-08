from __future__ import annotations

from dotenv import load_dotenv
from openai import OpenAI

from config_utils import get_config_value


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def get_llm_settings() -> tuple[str, str | None, str]:
    load_dotenv()

    groq_api_key = get_config_value("GROQ_API_KEY")
    openai_api_key = get_config_value("OPENAI_API_KEY")
    provider = (get_config_value("LLM_PROVIDER", "") or "").strip().lower()
    if not provider:
        provider = "groq" if groq_api_key or (openai_api_key or "").startswith("gsk_") else "openai"

    if provider == "groq":
        api_key = groq_api_key or openai_api_key
        model = get_config_value("GROQ_MODEL", DEFAULT_GROQ_MODEL) or DEFAULT_GROQ_MODEL
    elif provider == "openai":
        api_key = openai_api_key
        model = get_config_value("OPENAI_MODEL", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL
    else:
        raise ValueError("LLM_PROVIDER must be either 'groq' or 'openai'")

    return provider, api_key, model


def get_llm_model() -> str:
    return get_llm_settings()[2]


def create_llm_client(*, required: bool = False) -> tuple[OpenAI | None, str]:
    provider, api_key, model = get_llm_settings()
    if not api_key:
        if required:
            key_name = "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY"
            raise ValueError(f"Set {key_name} in .env to use the LLM")
        return None, model

    base_url = GROQ_BASE_URL if provider == "groq" else None
    return OpenAI(api_key=api_key, base_url=base_url), model