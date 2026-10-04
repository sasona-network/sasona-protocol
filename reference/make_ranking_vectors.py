"""Write vectors/ranking.json from the reference implementation.

    python make_ranking_vectors.py

Each expected result is written down here by hand and checked against the
reference, so the vectors are not simply whatever the code prints.
"""

import json
from pathlib import Path

import ranking as rk

DAY = 24 * 60 * 60
NOW = 100 * DAY
SLOT = 1_000_000


def r(id, quote, days_ago=1, slot=SLOT, **over):
    """A reading revealed `days_ago` days ago in `slot`, committed 10 slots before."""
    base = {"id": id, "revealed_slot": slot, "committed_slot": slot - 10, "revealed_time": NOW - days_ago * DAY,
            "counts": True, "verdict": 1, "member_active": True, "quote": quote, "quote_by_reader": True}
    base.update(over)
    return base


def main():
    premiums = [
        ("a standing quote", [r("aa", 120)], 120),
        ("the lowest rate, 1", [r("aa", 1)], 1),
        ("the highest rate, 10,000", [r("aa", 10_000)], 10_000),
        ("withdrawn", [r("aa", 0)], None),
        ("above 10,000", [r("aa", 10_001)], None),
        ("set by someone other than the reader", [r("aa", 120, quote_by_reader=False)], None),
        ("the member asked to leave", [r("aa", 120, member_active=False)], None),
        ("the current reading says wrong answer", [r("aa", 120, verdict=2)], None),
        ("the current reading says empty", [r("aa", 120, verdict=3)], None),
        ("revealed exactly 30 days ago", [r("aa", 120, days_ago=30)], 120),
        ("revealed 30 days and a second ago", [dict(r("aa", 120, days_ago=30), revealed_time=NOW - 30 * DAY - 1)], None),
        ("revealed after the moment asked about", [dict(r("aa", 120), revealed_time=NOW + 1)], None),
        ("no reading counts", [r("aa", 120, counts=False)], None),
        ("a newer reading that failed replaces a cheap old one",
         [r("aa", 5, days_ago=10, slot=SLOT), r("bb", 0, days_ago=2, slot=SLOT + 500, verdict=2)], None),
        ("a newer reading's own quote is the one that counts",
         [r("aa", 5, days_ago=10, slot=SLOT), r("bb", 400, days_ago=2, slot=SLOT + 500)], 400),
        ("a newer reading upheld false does not replace the old one",
         [r("aa", 50, days_ago=10, slot=SLOT), r("bb", 5, days_ago=2, slot=SLOT + 500, counts=False)], 50),
        ("revealed in the same slot: the one committed earliest is current",
         [r("aa", 50, committed_slot=SLOT - 3), r("bb", 70, committed_slot=SLOT - 9)], 70),
        ("same slot and commit: the smaller identifier is current",
         [r("bb", 50), r("aa", 70)], 70),
    ]
    premium_cases = []
    for name, readings, want in premiums:
        got = rk.premium(readings, NOW)
        assert got == want, (name, got, want)
        premium_cases.append({"name": name, "now": NOW, "readings": readings, "premium": got})

    rankings = [
        ("cheapest first", {
            "https://a.example/x": [r("01", 300)],
            "https://b.example/x": [r("02", 100)],
            "https://c.example/x": [r("03", 200)],
        }, [["https://b.example/x", 100], ["https://c.example/x", 200], ["https://a.example/x", 300]]),
        ("a service whose current reading failed is not listed", {
            "https://a.example/x": [r("01", 50, days_ago=9), r("04", 0, days_ago=1, slot=SLOT + 9, verdict=2)],
            "https://b.example/x": [r("02", 100)],
        }, [["https://b.example/x", 100]]),
        ("the same premium: the fresher reading first", {
            "https://a.example/x": [r("01", 100, slot=SLOT)],
            "https://b.example/x": [r("02", 100, slot=SLOT + 1)],
        }, [["https://b.example/x", 100], ["https://a.example/x", 100]]),
        ("the same premium and slot: the smaller reading first", {
            "https://a.example/x": [r("f0", 100)],
            "https://b.example/x": [r("0f", 100)],
        }, [["https://b.example/x", 100], ["https://a.example/x", 100]]),
        ("nothing listed", {"https://a.example/x": [r("01", 0)]}, []),
    ]
    rank_cases = []
    for name, services, want in rankings:
        got = [list(x) for x in rk.rank(services, NOW)]
        assert got == want, (name, got, want)
        rank_cases.append({"name": name, "now": NOW, "services": services, "ranking": got})

    out = {"version": "0.6.0", "term_seconds": rk.TERM_SECONDS, "premiums": premium_cases, "rankings": rank_cases}
    path = Path(__file__).parent.parent / "vectors" / "ranking.json"
    path.write_bytes((json.dumps(out, indent=1) + "\n").encode("ascii"))
    print(f"wrote {path}: {len(premium_cases)} premiums, {len(rank_cases)} rankings")


if __name__ == "__main__":
    main()
