"""
In-memory session storage.

Dev/demo only -- state is lost on server restart and won't work across multiple
worker processes. Fine for a final-year project running one uvicorn process.
Swap for a real DB (a `sessions` + `baseline_samples` + `question_results` table)
before this needs to survive a restart or handle concurrent users.
"""

import uuid
from dataclasses import dataclass, field
import numpy as np

from .scoring import BaselineProfile


@dataclass
class Session:
    session_id: str
    baseline_vectors: list[np.ndarray] = field(default_factory=list)
    baseline_profile: BaselineProfile | None = None
    results: list[dict] = field(default_factory=list)


_sessions: dict[str, Session] = {}


def create_session() -> Session:
    session_id = str(uuid.uuid4())
    session = Session(session_id=session_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session:
    session = _sessions.get(session_id)
    if session is None:
        raise KeyError(f"No session found for id {session_id}")
    return session
