"""Quotes and the ranking, as SPEC.md section 6 defines them. Standard library only."""

TERM_SECONDS = 30 * 24 * 60 * 60
DELIVERED = 1


def stands(q: dict, at: int) -> bool:
    """SPEC.md 6.1 and 6.2: whether a quote stands at time `at`.

    A quote is a dict: "reading" (hex identifier), "rate" (basis points, 0 if
    withdrawn), "counts" (its reading passes 2.7 and was not upheld false),
    "verdict", "by_reader" (set by the key that took the reading),
    "by_member" (the reading was taken by a member), "revealed_time" and
    "member_active" (its membership is active at `at`)."""
    return (1 <= q["rate"] <= 10_000 and q["counts"] and q["verdict"] == DELIVERED and q["by_reader"]
            and q["by_member"] and q["member_active"] and at <= q["revealed_time"] + TERM_SECONDS)


def rank(services: dict, at: int) -> list:
    """SPEC.md 6.3: [(service, premium)], in order. `services` maps each
    service to the quotes on its readings."""
    priced = []
    for service, quotes in services.items():
        standing = [q for q in quotes if stands(q, at)]
        if not standing:
            continue
        best = min(standing, key=lambda q: (q["rate"], -q["revealed_time"], bytes.fromhex(q["reading"])))
        priced.append((best["rate"], -best["revealed_time"], bytes.fromhex(best["reading"]), service))
    priced.sort()
    return [(service, rate) for rate, _, _, service in priced]
