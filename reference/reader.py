"""Drawing the member who reads a service, as SPEC.md 4.3 defines it. Standard library only."""

import hashlib
import hmac

MAX_ATTEMPTS = 16


def n(final: bytes, service: str, attempt: int, members: int) -> int:
    """The membership drawn at this attempt, numbered from 1."""
    message = b"reader" + hashlib.sha256(service.encode("ascii")).digest() + attempt.to_bytes(4, "big")
    digest = hmac.new(final, message, hashlib.sha256).digest()
    return 1 + int.from_bytes(digest, "big") % members


def reader(final: bytes, service: str, memberships: list, first_reader=None):
    """The membership that reads `service`, or None.

    `memberships` is the round's roster, in order: membership k is
    memberships[k - 1], a dict with "key" and "active" (at the reading's
    commit). `first_reader` is the key that took the first reading, for a
    second reading."""
    members = len(memberships)
    if members == 0:
        return None
    for attempt in range(MAX_ATTEMPTS):
        k = n(final, service, attempt, members)
        m = memberships[k - 1]
        if m["active"] and m["key"] != first_reader:
            return k
    return None
