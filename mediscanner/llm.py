import logging
import os
from typing import Literal, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


Provider = Literal["groq", "xai"]


def _normalize_provider(value: Optional[str]) -> Optional[Provider]:
    if not value:
        return None
    value_norm = value.strip().lower()
    if value_norm in {"groq"}:
        return "groq"
    if value_norm in {"xai", "grok"}:
        return "xai"
    return None


def pick_provider() -> Provider:
    """Pick which chat provider to use.

    Order:
    1) `AI_PROVIDER` if set to `groq` or `xai`/`grok`
    2) If `XAI_API_KEY`/`GROK_API_KEY` is set (and `GROQ_API_KEY` is not), use xAI
    3) Otherwise default to Groq
    """

    explicit = _normalize_provider(os.getenv("AI_PROVIDER"))
    if explicit:
        return explicit

    has_xai = bool(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))

    if has_xai and not has_groq:
        return "xai"

    return "groq"


def create_chat_model(*, temperature: float = 0.3):
    provider = pick_provider()

    if provider == "groq":
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing GROQ_API_KEY. If you intended to use Grok (xAI), set AI_PROVIDER=xai and XAI_API_KEY (or GROK_API_KEY)."
            )

        model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        return ChatGroq(api_key=api_key, model=model_name, temperature=temperature)

    # provider == "xai"
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "xAI provider selected but dependency 'langchain-openai' is not installed. "
            "Add 'langchain-openai' and 'openai' to requirements.txt and redeploy."
        ) from exc

    api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing XAI_API_KEY (or GROK_API_KEY). If you intended to use Groq, set GROQ_API_KEY instead."
        )

    # Common misconfig: Groq keys often start with "gsk_" and will not work for xAI.
    if api_key.strip().startswith("gsk_"):
        raise RuntimeError(
            "XAI_API_KEY appears to be a Groq key (starts with 'gsk_'). "
            "For Groq set AI_PROVIDER=groq and use GROQ_API_KEY. "
            "For Grok (xAI), get an xAI API key from https://console.x.ai and set XAI_API_KEY."
        )

    base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
    # Default to a model name that is commonly enabled across xAI accounts.
    # If your account supports newer aliases (e.g. grok-2-*), set XAI_MODEL explicitly.
    model_name = os.getenv("XAI_MODEL", "grok-beta")

    logger.info("Using xAI provider with model=%s base_url=%s", model_name, base_url)

    return ChatOpenAI(api_key=api_key, base_url=base_url, model=model_name, temperature=temperature)
