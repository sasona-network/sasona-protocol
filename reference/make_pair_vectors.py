"""Write vectors/pair.json from the reference implementation.

    python make_pair_vectors.py
"""

import json
from pathlib import Path

import pair as p

NAMES = {1: "delivered", 2: "wrong_answer", 3: "empty"}


def main():
    outcomes = [{"first": a, "second": b, "first_name": NAMES[a], "second_name": NAMES[b],
                 "outcome": p.outcome(a, b), "outcome_name": p.OUTCOMES[p.outcome(a, b)]}
                for a in (1, 2, 3) for b in (1, 2, 3)]
    base = dict(first_reader="A", second_reader="B", first_revealed_slot=100, second_committed_slot=200,
                same_service=True, same_round=False)
    cases = [
        ("a fair second reading", {}, True),
        ("the same reader", {"second_reader": "A"}, False),
        ("committed before the first was revealed", {"second_committed_slot": 90}, False),
        ("committed in the slot the first was revealed", {"second_committed_slot": 100}, False),
        ("a different service", {"same_service": False}, False),
        ("the same round", {"same_round": True}, False),
    ]
    counting = [{"name": n, **{**base, **c}, "counts": want} for n, c, want in cases]
    for c in counting:
        args = {k: c[k] for k in base}
        assert p.counts(**args) == c["counts"], c["name"]
    out = {"version": "0.4.0", "outcomes": outcomes, "counting": counting}
    path = Path(__file__).parent.parent / "vectors" / "pair.json"
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="ascii", newline="\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
