"""
rag/memory.py — Redis-Backed Conversation Memory
=================================================
Wraps LangChain's RedisChatMessageHistory with helpers used by chain.py.

Features:
  - Windowed history (last K turns) to stay within context limits
  - Graceful fallback to in-memory list if Redis is unavailable
  - Session isolation: each session_id has its own history

Usage:
    from rag.memory import get_session_history, format_history

    history = get_session_history("session-abc-123")
    history.add_user_message("Hello")
    history.add_ai_message("Hi! How can I help?")

    text = format_history(history, window_k=10)
"""

import logging
from typing import List

from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage

from config import settings

logger = logging.getLogger(__name__)

# ── In-memory fallback ───────────────────────────────────────────────────────

class _InMemoryHistory(BaseChatMessageHistory):
    """Minimal in-memory chat history for when Redis is unavailable."""

    def __init__(self):
        self._messages: List[BaseMessage] = []

    @property
    def messages(self) -> List[BaseMessage]:
        return self._messages

    def add_message(self, message: BaseMessage) -> None:
        self._messages.append(message)

    def clear(self) -> None:
        self._messages.clear()


# ── Public API ───────────────────────────────────────────────────────────────

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    Return the chat message history for a given session.
    Falls back to in-memory storage if Redis is unreachable.

    Parameters
    ----------
    session_id : Unique identifier for the conversation session

    Returns
    -------
    BaseChatMessageHistory implementation
    """
    try:
        history = RedisChatMessageHistory(session_id, url=settings.REDIS_URL)
        # Quick connectivity test — will raise on connection failure
        _ = history.messages
        return history
    except Exception as e:
        logger.warning(
            f"Redis unavailable ({e}). Falling back to in-memory session history "
            f"for session '{session_id}'. Conversation will not persist across restarts."
        )
        return _InMemoryHistory()


def format_history(history: BaseChatMessageHistory, window_k: int = 10) -> str:
    """
    Format the last `window_k` message pairs as a plain-text string
    suitable for injection into the system prompt context.

    Parameters
    ----------
    history  : Chat message history object
    window_k : Number of most recent turns to include

    Returns
    -------
    Multi-line string with "human: ..." and "ai: ..." lines
    """
    messages = history.messages
    # Take the last window_k*2 messages (each turn = 1 human + 1 ai)
    recent   = messages[-(window_k * 2):]

    if not recent:
        return "(Pas d'historique de conversation)"

    lines = []
    for msg in recent:
        role   = "Utilisateur" if msg.type == "human" else "Assistant"
        # Truncate very long messages to keep prompt size manageable
        content = msg.content[:500] + "…" if len(msg.content) > 500 else msg.content
        lines.append(f"{role} : {content}")

    return "\n".join(lines)


def clear_session(session_id: str) -> bool:
    """
    Clear all messages for a session. Returns True on success.
    Used by admin endpoints to reset conversations.
    """
    try:
        history = get_session_history(session_id)
        history.clear()
        logger.info(f"Session '{session_id}' cleared.")
        return True
    except Exception as e:
        logger.error(f"Failed to clear session '{session_id}': {e}")
        return False
