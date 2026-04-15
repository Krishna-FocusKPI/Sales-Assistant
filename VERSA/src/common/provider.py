"""
Provider factory for the LangGraph rebuild.
Returns a chat model (OpenAI or Anthropic) and embedding model for the agent.

Configuration (no legacy flat keys):
  - Environment: OPENAI_API_KEY, OPENAI_MODEL, OPENAI_EMBEDDING_MODEL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    LLM_PROVIDER, EMBEDDING_PROVIDER.
  - Or Streamlit secrets.toml: [openai] api_key, model, embedding_model; [anthropic] api_key, model;
    optional [llm] provider, [embedding] provider.

Embeddings use OpenAI only; when EMBEDDING_PROVIDER=anthropic, OpenAI embeddings are still used (set OPENAI_API_KEY).
"""
import logging
import os
from typing import Literal, Any

SUPPORTED_PROVIDERS = ("openai", "anthropic")
ProviderName = Literal["openai", "anthropic"]

# Recommended embedding models (OpenAI; Anthropic has no embedding API)
OPENAI_EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"
OPENAI_EMBEDDING_MODELS = ("text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002")


def _st_secrets_get(section: str, field: str) -> str:
    """Read st.secrets[section][field] using bracket access (works when hasattr(section) is unreliable)."""
    try:
        import streamlit as st
        if section not in st.secrets:
            return ""
        node = st.secrets[section]
        if isinstance(node, dict):
            return str(node.get(field, "") or "").strip()
        if hasattr(node, field):
            return str(getattr(node, field, "") or "").strip()
        return str(node[field] or "").strip()
    except Exception:
        return ""


def get_default_provider() -> ProviderName:
    """Default LLM provider for CBT and other flows. From env LLM_PROVIDER or st.secrets, else 'openai'."""
    value = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if value in SUPPORTED_PROVIDERS:
        return value  # type: ignore
    p = _st_secrets_get("llm", "provider").lower()
    if p in SUPPORTED_PROVIDERS:
        return p  # type: ignore
    return "openai"


def _get_config(key: str, default: str = "") -> str:
    """Read config from env; in Streamlit, from st.secrets ([openai], [anthropic], [embedding])."""
    value = os.environ.get(key, default).strip()
    if value:
        return value
    if key == "OPENAI_API_KEY":
        v = _st_secrets_get("openai", "api_key")
        return v if v else ""
    if key == "OPENAI_MODEL":
        v = _st_secrets_get("openai", "model")
        return v if v else ""
    if key == "OPENAI_EMBEDDING_MODEL":
        v = _st_secrets_get("openai", "embedding_model")
        return v if v else ""
    if key == "ANTHROPIC_API_KEY":
        v = _st_secrets_get("anthropic", "api_key")
        return v if v else ""
    if key == "ANTHROPIC_MODEL":
        v = _st_secrets_get("anthropic", "model")
        return v if v else ""
    if key == "EMBEDDING_PROVIDER":
        v = _st_secrets_get("embedding", "provider")
        return v if v else ""
    return ""


def get_chat_model(
    provider: ProviderName,
    *,
    temperature: float = 0,
    model: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Return a LangChain chat model for the given provider.
    Uses OPENAI_API_KEY, OPENAI_MODEL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    (from env or st.secrets) unless overridden.
    """
    if provider == "openai":
        api_key = kwargs.get("api_key") or _get_config("OPENAI_API_KEY")
        model_name = model or kwargs.get("model") or _get_config("OPENAI_MODEL")
        if not api_key:
            raise ValueError(
                "OpenAI API key missing. Set env OPENAI_API_KEY or secrets.toml section [openai] with api_key=.... "
                "On DigitalOcean App Platform, set the Web Service secret VERSA_STREAMLIT_SECRETS_B64 to the "
                "base64 encoding of your full secrets.toml (UTF-8), redeploy, and check Runtime logs for decode errors."
            )
        if not model_name:
            raise ValueError(
                "OPENAI_MODEL missing. Set env OPENAI_MODEL or [openai] model in secrets.toml."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=temperature,
            **{k: v for k, v in kwargs.items() if k not in ("api_key", "model")},
        )
    if provider == "anthropic":
        api_key = kwargs.get("api_key") or _get_config("ANTHROPIC_API_KEY")
        model_name = model or kwargs.get("model") or _get_config("ANTHROPIC_MODEL")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY (or api_key) is required for provider 'anthropic'")
        if not model_name:
            raise ValueError("ANTHROPIC_MODEL must be set in secrets or env for provider 'anthropic'")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            **{k: v for k, v in kwargs.items() if k not in ("api_key", "model")},
        )
    raise ValueError(f"Unsupported provider: {provider}. Use one of {SUPPORTED_PROVIDERS}")


def _get_embedding_provider() -> str:
    """Resolve embedding provider: env EMBEDDING_PROVIDER or st.secrets.embedding.provider, else 'openai'."""
    value = os.environ.get("EMBEDDING_PROVIDER", "").strip().lower()
    if value in SUPPORTED_PROVIDERS:
        return value
    p = _st_secrets_get("embedding", "provider").lower()
    if p in SUPPORTED_PROVIDERS:
        return p
    return "openai"


def get_openai_embeddings(
    *,
    model: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Return OpenAI embeddings for RAG. Uses OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL
    (or st.secrets.openai.embedding_model). Default model: text-embedding-3-small.
    """
    api_key = kwargs.get("openai_api_key") or _get_config("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings (set in env or secrets)")
    model_name = model or kwargs.get("model") or _get_config("OPENAI_EMBEDDING_MODEL") or OPENAI_EMBEDDING_MODEL_DEFAULT
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(openai_api_key=api_key, model=model_name, **{k: v for k, v in kwargs.items() if k not in ("openai_api_key", "model")})


def get_embeddings(
    provider: str | None = None,
    *,
    model: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Return embeddings for RAG (filter_product, reset_filter). Supports provider 'openai'.
    Anthropic does not offer embedding models; when provider is 'anthropic' we use OpenAI
    embeddings (OPENAI_API_KEY required) and log. Env: EMBEDDING_PROVIDER; secrets: embedding.provider.
    """
    prov = (provider or _get_embedding_provider()).lower()
    if prov == "anthropic":
        logging.getLogger(__name__).info(
            "Anthropic does not provide embedding models; using OpenAI for embeddings. Set OPENAI_API_KEY."
        )
        return get_openai_embeddings(model=model, **kwargs)
    if prov == "openai":
        return get_openai_embeddings(model=model, **kwargs)
    raise ValueError(f"Unsupported embedding provider: {prov}. Use 'openai' or 'anthropic' (anthropic uses OpenAI under the hood).")
