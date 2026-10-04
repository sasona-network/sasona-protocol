"""Quotes and the ranking, as SPEC.md section 6 defines them. Standard library only."""

TERM_SECONDS = 30 * 24 * 60 * 60
DELIVERED = 1


def order(r: dict):
    """SPEC.md 3.2's order, latest first: the smallest key is the latest."""
    return (-r["revealed_slot"], r["committed_slot"], bytes.fromhex(r["id"]))


def weighed(readings: list, now: int) -> list:
    """SPEC.md 6.2: the readings that count and were revealed by `now`, latest first.

    A reading is a dict: "id" (hex), "key" (who took it), "revealed_slot",
    "committed_slot", "revealed_time", "counts" (passes 2.7 and was not
    upheld false), "verdict", "member_active", and "quote": its rate, 0 if
    none or withdrawn, with "quote_by_reader" saying the reader set it."""
    return sorted((r for r in readings if r["counts"] and r["revealed_time"] <= now), key=order)


def newer_than_failing_pair(readings: list, now: int) -> list:
    """SPEC.md 6.2: the weighed readings newer than the latest failing pair,
    all of them if there is none."""
    w = weighed(readings, now)
    for i in range(len(w) - 1):
        a, b = w[i], w[i + 1]
        if a["verdict"] != DELIVERED and b["verdict"] != DELIVERED and a["key"] != b["key"]:
            return w[:i]
    return w


def stands(r: dict, now: int) -> bool:
    """SPEC.md 6.2: whether the quote on a weighed reading stands at `now`."""
    return (r["verdict"] == DELIVERED and now <= r["revealed_time"] + TERM_SECONDS
            and 1 <= r["quote"] <= 10_000 and r["quote_by_reader"] and r["member_active"])


def behind(readings: list, now: int):
    """SPEC.md 6.3 steps 1 and 2: the reading whose quote is the premium, or None if not listed."""
    standing = [r for r in newer_than_failing_pair(readings, now) if stands(r, now)]
    return min(standing, key=lambda r: (r["quote"], order(r))) if standing else None


def premium(readings: list, now: int):
    r = behind(readings, now)
    return r["quote"] if r else None


def rank(services: dict, now: int) -> list:
    """SPEC.md 6.3: [(service, premium)], in order. `services` maps each
    service to its readings."""
    listed = []
    for service, readings in services.items():
        r = behind(readings, now)
        if r is not None:
            listed.append((r["quote"], order(r), service))
    listed.sort()
    return [(service, p) for p, _, service in listed]
