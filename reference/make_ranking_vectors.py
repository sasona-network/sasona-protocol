"""Write vectors/ranking.json from the reference implementation.

    python make_ranking_vectors.py
"""

import json
from pathlib import Path

import ranking as rk

DAY = 24 * 60 * 60
T = 100 * DAY


def q(reading, rate, revealed_days_ago=1, **over):
    base = {"reading": reading, "rate": rate, "counts": True, "verdict": 1, "by_reader": True, "by_member": True,
            "revealed_time": T - revealed_days_ago * DAY, "member_active": True}
    base.update(over)
    return base


def main():
    standing = [
        ("a standing quote", q("aa", 120), True),
        ("withdrawn", q("aa", 0), False),
        ("a rate above 10,000", q("aa", 10_001), False),
        ("a reading upheld false", q("aa", 120, counts=False), False),
        ("a reading that did not deliver", q("aa", 120, verdict=2), False),
        ("set by someone other than the reader", q("aa", 120, by_reader=False), False),
        ("on a reading taken before members", q("aa", 120, by_member=False), False),
        ("the member asked to leave", q("aa", 120, member_active=False), False),
        ("revealed exactly 30 days ago", q("aa", 120, revealed_days_ago=30), True),
        ("revealed 30 days and a second ago", dict(q("aa", 120, revealed_days_ago=30), revealed_time=T - 30 * DAY - 1), False),
    ]
    stand_cases = [{"name": n, "quote": x, "at": T, "stands": rk.stands(x, T)} for n, x, want in standing]
    for c, (_, _, want) in zip(stand_cases, standing):
        assert c["stands"] == want, c["name"]

    rankings = [
        ("cheapest first", {
            "https://a.example/x": [q("01", 300)],
            "https://b.example/x": [q("02", 100)],
            "https://c.example/x": [q("03", 200)],
        }),
        ("a service's premium is its lowest standing quote", {
            "https://a.example/x": [q("01", 300), q("04", 90), q("05", 50, counts=False)],
            "https://b.example/x": [q("02", 100)],
        }),
        ("a service with no standing quote is not listed", {
            "https://a.example/x": [q("01", 300, member_active=False)],
            "https://b.example/x": [],
            "https://c.example/x": [q("03", 200)],
        }),
        ("the same premium: the fresher reading first", {
            "https://a.example/x": [q("01", 100, revealed_days_ago=5)],
            "https://b.example/x": [q("02", 100, revealed_days_ago=2)],
        }),
        ("the same premium and reveal: the smaller reading first", {
            "https://a.example/x": [q("f0", 100)],
            "https://b.example/x": [q("0f", 100)],
        }),
        ("nothing stands", {"https://a.example/x": [q("01", 0)]}),
    ]
    rank_cases = [{"name": n, "at": T, "services": s, "ranking": [list(x) for x in rk.rank(s, T)]} for n, s in rankings]
    out = {"version": "0.6.0", "term_seconds": rk.TERM_SECONDS, "standing": stand_cases, "rankings": rank_cases}
    path = Path(__file__).parent.parent / "vectors" / "ranking.json"
    path.write_bytes((json.dumps(out, indent=1) + "\n").encode("ascii"))
    print(f"wrote {path}")
    for c in rank_cases:
        print(f"  {c['name']}: {c['ranking']}")


if __name__ == "__main__":
    main()
