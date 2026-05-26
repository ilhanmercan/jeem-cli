from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from jeem.models import Message, Session, TextPart

SESSIONS_DIR = Path.home() / ".jeem" / "sessions"


def _ensure_dir() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR


def _path(name: str) -> Path:
    return _ensure_dir() / f"{name}.json"


def generate_id() -> str:
    return uuid.uuid4().hex[:16]


def new_chat_id() -> str:
    return generate_id()


def new_message_id() -> str:
    return generate_id()


def create_message(text: str, role: str = "user") -> Message:
    return Message(parts=[TextPart(text=text)], id=new_message_id(), role=role)


def load(name: str) -> Session | None:
    path = _path(name)
    if not path.exists():
        return None
    return Session(**json.loads(path.read_text()))


def save(session: Session) -> None:
    session.updated_at = datetime.now()
    _path(session.name).write_text(session.model_dump_json(indent=2))


def delete(name: str) -> bool:
    path = _path(name)
    if path.exists():
        path.unlink()
        return True
    return False


def list_all() -> list[Session]:
    sessions = []
    for f in sorted(_ensure_dir().glob("*.json")):
        try:
            sessions.append(Session(**json.loads(f.read_text())))
        except Exception:
            pass
    return sessions
