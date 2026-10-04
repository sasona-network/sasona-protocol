"""Drawing the member who reads a service, as SPEC.md 4.3 defines it. Standard library only."""

import hashlib
import hmac

MAX_ATTEMPTS = 16


def s(final: bytes, service: str, attempt: int, members: int) -> int:
    """The seat drawn at this attempt, numbered from 1, out of the round's M."""
    message = b"reader" + hashlib.sha256(service.encode("ascii")).digest() + attempt.to_bytes(4, "big")
    digest = hmac.new(final, message, hashlib.sha256).digest()
    return 1 + int.from_bytes(digest, "big") % members


def reader(final: bytes, service: str, members: int, committed_slot: int, seats: list, first_reader=None):
    """The seat whose membership reads `service`, or None.

    `members` is M and `committed_slot` the slot the round was committed in.
    `seats` is the roster when the reading is committed: seats[k - 1] is a
    dict with the "key" holding the membership in seat k and the slot it sat
    down in, "since"; len(seats) is A. `first_reader` is the key that took
    the first reading, for a second reading."""
    if members == 0:
        return None
    for attempt in range(MAX_ATTEMPTS):
        k = s(final, service, attempt, members)
        if k > len(seats):
            continue
        seat = seats[k - 1]
        if seat["since"] < committed_slot and seat["key"] != first_reader:
            return k
    return None
