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


def roster(keys, inactive=()):
    return [{"key": k, "active": i + 1 not in inactive} for i, k in enumerate(keys)]


def main():
    five = ["A", "B", "C", "D", "E"]
    cases = [
        ("one membership", final_of("one"), SERVICE, roster(["A"]), None),
        ("five memberships", final_of("five"), SERVICE, roster(five), None),
        ("another service, the same seed", final_of("five"), "https://data.example.com/prices", roster(five), None),
        ("no memberships", final_of("none"), SERVICE, [], None),
        ("one key holding three of five", final_of("three"), SERVICE, roster(["A", "A", "A", "B", "C"]), None),
        ("every membership inactive", final_of("idle"), SERVICE, roster(five, inactive={1, 2, 3, 4, 5}), None),
        ("a second reading, only the first reader active", final_of("only"), SERVICE, roster(["A", "B"], inactive={2}), "A"),
    ]
    # Cases where the first draw is skipped, found by searching seeds, so the
    # skip rules are exercised and not only stated.
    for name, make, first in [
        ("the first draw is inactive", lambda k: roster(five, inactive={k}), None),
        ("the first draw is the first reader's key", lambda k: roster(five), None),
    ]:
        for i in range(1000):
            f = final_of(f"{name} {i}")
            k = rd.n(f, SERVICE, 0, 5)
            if rd.n(f, SERVICE, 1, 5) != k:
                break
        r = make(k)
        cases.append((name, f, SERVICE, r, r[k - 1]["key"] if "reader's key" in name else first))

    out_cases = []
    for name, f, service, ms, first in cases:
        attempts = [rd.n(f, service, a, len(ms)) for a in range(rd.MAX_ATTEMPTS)] if ms else []
        out_cases.append({"name": name, "final_seed": f.hex(), "service": service, "memberships": ms,
                          "first_reader": first, "attempts": attempts,
                          "reader": rd.reader(f, service, ms, first)})
    out = {"version": "0.5.0", "max_attempts": rd.MAX_ATTEMPTS, "cases": out_cases}
    path = Path(__file__).parent.parent / "vectors" / "reader.json"
    path.write_bytes((json.dumps(out, indent=1) + "\n").encode("ascii"))
    print(f"wrote {path}")
    for c in out_cases:
        print(f"  {c['name']}: {c['reader']}   first draws {c['attempts'][:3]}")


if __name__ == "__main__":
    main()
