from __future__ import annotations

import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def get_config_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        secret = st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default

    return str(secret) if secret is not None else default
