import os
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .llm import create_chat_model, pick_provider

load_dotenv()

logger = logging.getLogger(__name__)


class SymptomAgent:
    def __init__(self):
        self.provider = pick_provider()
        self.model = create_chat_model(temperature=0.3)

    def reply(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        system_instructions = (
            "You are MediNudge AI Doctor, a medical guidance assistant. "
            "Provide general health information and triage guidance, not a diagnosis. "
            "Be calm, clear, and concise. "
            "Do not provide medication dosing. "
            "If symptoms suggest a potential emergency, clearly advise urgent care/emergency services. "
            "When information is insufficient, ask up to 3 targeted follow-up questions. "
            "Always include a brief disclaimer that this is not medical advice and to consult a licensed clinician. "
            "Output plain text only (no HTML)."
        )

        messages = [SystemMessage(content=system_instructions)]

        if history:
            for turn in history[-10:]:
                role = (turn.get("role") or "").lower().strip()
                content = (turn.get("content") or "").strip()
                if not content:
                    continue
                if role in {"user", "human"}:
                    messages.append(HumanMessage(content=content))
                elif role in {"ai", "assistant"}:
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=message.strip()))

        try:
            response = self.model.invoke(messages)
        except Exception:
            logger.exception("AI model invocation failed (provider=%s)", getattr(self, "provider", "unknown"))
            raise

        return (getattr(response, "content", None) or "").strip()
