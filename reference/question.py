"""The committed question, as SPEC.md section 2 defines it. Standard library only."""

import hashlib
import json
import re

DELIVERED, WRONG_ANSWER, EMPTY = 1, 2, 3
VERDICTS = {DELIVERED: "delivered", WRONG_ANSWER: "wrong_answer", EMPTY: "empty"}

NONCE = re.compile(r"[0-9a-f]{32}")


def _nonce(nonce: str) -> str:
    if not isinstance(nonce, str) or not NONCE.fullmatch(nonce):
        raise ValueError("a nonce is 32 lowercase hex characters")
    return nonce


def expected(nonce: str) -> str:
    return hashlib.sha256(_nonce(nonce).encode("ascii")).hexdigest()[:16]


def code_for(nonce: str) -> str:
    return 'import hashlib\nprint(hashlib.sha256("' + _nonce(nonce) + '".encode()).hexdigest()[:16])'


def question(nonce: str) -> dict:
    """SPEC.md 2.2, as an object."""
    code = code_for(nonce)
    return {
        "capability": "execute",
        "nonce": nonce,
        "expect": expected(nonce),
        "tier": 1,
        "code": code,
        "command": ["python", "-c", code],
        "body": {"code": code, "language": "python"},
    }


def canonical(nonce: str) -> bytes:
    """SPEC.md 2.3: the one byte sequence for this nonce's question."""
    return json.dumps(question(nonce), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def question_hash(nonce: str) -> bytes:
    return hashlib.sha256(canonical(nonce)).digest()


def is_fair(shown: bytes) -> bool:
    """Whether some bytes are exactly the canonical question for the nonce they name."""
    try:
        nonce = json.loads(shown)["nonce"]
        return shown == canonical(nonce)
    except (ValueError, TypeError, KeyError):
        return False


MAX_REPLY_BYTES = 10_000


def recorded(received: bytes) -> bytes:
    """SPEC.md 2.4: the reply is the first 10,000 bytes of what came back."""
    return received[:MAX_REPLY_BYTES]


def reply_hash(received: bytes) -> bytes:
    return hashlib.sha256(recorded(received)).digest()


def verdict(received: bytes, nonce: str) -> int:
    """SPEC.md 2.4."""
    reply = recorded(received)
    if not reply:
        return EMPTY
    return DELIVERED if expected(nonce).encode("ascii") in reply else WRONG_ANSWER
