"""Write vectors/reader.json from the reference implementation.

    python make_reader_vectors.py
"""

import hashlib
import json
from pathlib import Path

import reader as rd

SERVICE = "https://sandbox.example.net/run/python"


def final_of(label: str) -> bytes:
    return hashlib.sha256(label.encode()).digest()


def find(name, members, want):
    """A seed whose draws satisfy `want`, so a rule is exercised and not only stated."""
    for i in range(10_000):
        f = final_of(f"{name} {i}")
        draws = [rd.s(f, SERVICE, a, members) for a in range(rd.MAX_ATTEMPTS)]
        if want(draws):
            return f
    raise SystemExit(f"no seed for {name}")


def main():
    five = ["A", "B", "C", "D", "E"]
    cases = [
        ("one seat", final_of("one"), SERVICE, 1, ["A"], None),
        ("five seats", final_of("five"), SERVICE, 5, five, None),
        ("another service, the same seed", final_of("five"), "https://data.example.com/prices", 5, five, None),
        ("no seats when the round was committed", final_of("none"), SERVICE, 0, ["A"], None),
        ("one key in three of five seats", final_of("three"), SERVICE, 5, ["A", "A", "A", "B", "C"], None),
        ("every seat emptied since", final_of("gone"), SERVICE, 5, [], None),
        ("a second reading, only the first reader seated", final_of("only"), SERVICE, 2, ["A", "A"], "A"),
    ]
    f = find("first draw beyond the roster now", 5, lambda d: d[0] == 5 and d[1] != 5)
    cases.append(("the first seat drawn is no longer there", f, SERVICE, 5, five[:4], None))
    f = find("first draw the first reader", 5, lambda d: d[0] != d[1])
    k = rd.s(f, SERVICE, 0, 5)
    cases.append(("the first seat drawn is the first reader's", f, SERVICE, 5, five, five[k - 1]))
    f = find("roster grew", 3, lambda d: True)
    cases.append(("seats taken after the round are never drawn", f, SERVICE, 3, five, None))

    out_cases = []
    for name, f, service, members, seats, first in cases:
        attempts = [rd.s(f, service, a, members) for a in range(rd.MAX_ATTEMPTS)] if members else []
        out_cases.append({"name": name, "final_seed": f.hex(), "service": service, "members": members,
                          "seats": seats, "first_reader": first, "attempts": attempts,
                          "reader": rd.reader(f, service, members, seats, first)})
    out = {"version": "0.5.0", "max_attempts": rd.MAX_ATTEMPTS, "cases": out_cases}
    path = Path(__file__).parent.parent / "vectors" / "reader.json"
    path.write_bytes((json.dumps(out, indent=1) + "\n").encode("ascii"))
    print(f"wrote {path}")
    for c in out_cases:
        print(f"  {c['name']}: seat {c['reader']}   draws {c['attempts']}  seed {c['final_seed']}")


if __name__ == "__main__":
    main()
