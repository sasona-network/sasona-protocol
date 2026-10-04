"""Quotes and the ranking, as SPEC.md section 6 defines them. Standard library only."""

TERM_SECONDS = 30 * 24 * 60 * 60
DELIVERED = 1


def order(r: dict):
    """SPEC.md 3.2's order, latest first: the smallest key is the latest."""
    return (-r["revealed_slot"], r["committed_slot"], bytes.fromhex(r["id"]))


def current(readings: list):
    """SPEC.md 6.2: the latest reading that counts, or None.

    A reading is a dict: "id" (hex), "revealed_slot", "committed_slot",
    "revealed_time", "counts" (passes 2.7 and was not upheld false),
    "verdict", "member_active", and "quote": its rate, 0 if none or
    withdrawn, with "quote_by_reader" saying the reader set it."""
    counting = [r for r in readings if r["counts"]]
    return min(counting, key=order) if counting else None


def premium(readings: list, now: int):
    """SPEC.md 6.3 step 1 and 2: the service's premium now, or None if it is not listed."""
    r = current(readings)
    if r is None or r["verdict"] != DELIVERED:
        return None
    if not (r["revealed_time"] <= now <= r["revealed_time"] + TERM_SECONDS):
        return None
    if not (1 <= r["quote"] <= 10_000 and r["quote_by_reader"] and r["member_active"]):
        return None
    return r["quote"]


def rank(services: dict, now: int) -> list:
    """SPEC.md 6.3: [(service, premium)], in order. `services` maps each
    service to its readings."""
    listed = []
    for service, readings in services.items():
        p = premium(readings, now)
        if p is not None:
            listed.append((p, order(current(readings)), service))
    listed.sort()
    return [(service, p) for p, _, service in listed]
