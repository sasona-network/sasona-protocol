"""Write vectors/draw.json from the reference implementation.

    python make_vectors.py

Run it only when the spec changes, which is a new major version. Every
implementation, this one included, is then checked against the file.
"""

import hashlib
import json
from pathlib import Path

import draw as d

SEED = bytes(range(32))
OTHER_SEED = bytes(range(32, 64))
ENTROPY = hashlib.sha256(b"an example slot hash").digest()

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = ALPHABET[r] + out
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + out


HOSTS = [
    "https://Shop.Example.com/a",
    "https://user@shop.example.com:443/a",
    "https://user:pw@shop.example.com/a@b",
    "http://shop.example.com.:80?q=1",
    "http://shop.example.com:443/x",
    "https://shop.example.com:8443/a",
    "HTTPS://shop.example.com#frag",
    "https://[::1]:443/x",
    "https://[::1]:8443/x",
    "http://bare.example.net",
]

ONE_HOST = [f"https://a.example.com/service/{i}" for i in range(5)]
MANY_HOSTS = (
    [f"https://big.example.com/api/{i}" for i in range(12)]
    + ["https://small.example.org/only"]
    + [f"https://MIXED.Example.net:8443/v{i}" for i in range(3)]
    + ["http://bare.example.net"]
)
SAME_SERVICE_SPELT_DIFFERENTLY = [
    "https://a.example.com/x",
    "https://A.example.com/x",
    "https://a.example.com:443/x",
    "https://other.example.org/y",
]
CAP_REACHED = [f"https://single{i}.example.org/x" for i in range(30)] + [
    f"https://huge.example.com/item/{i}" for i in range(1000)
]

REFUSED = [
    {"why": "a candidate appears twice", "candidates": ["https://x.example/a", "https://x.example/a"], "count": 1},
    {"why": "count is zero", "candidates": ["https://x.example/a"], "count": 0},
    {"why": "count is more than the list", "candidates": ["https://x.example/a"], "count": 2},
    {"why": "an empty list", "candidates": [], "count": 1},
    {"why": "not http or https", "candidates": ["ftp://x.example/a"], "count": 1},
    {"why": "no scheme", "candidates": ["x.example/a"], "count": 1},
    {"why": "not ASCII", "candidates": ["https://İ.example/a"], "count": 1},
    {"why": "a space", "candidates": ["https://x.example/a b"], "count": 1},
    {"why": "an empty host", "candidates": ["https:///x"], "count": 1},
    {"why": "only userinfo", "candidates": ["https://user@/x"], "count": 1},
]


def case(name, candidates, seed, entropy, count):
    final = d.final_seed(seed, entropy)
    return {
        "name": name,
        "candidates": candidates,
        "seed": seed.hex(),
        "entropy": entropy.hex(),
        "entropy_base58": b58(entropy),
        "count": count,
        "seed_hash": d.seed_hash(seed).hex(),
        "pool_fingerprint": d.pool_fingerprint(candidates).hex(),
        "final_seed": final.hex(),
        "picks": d.draw(candidates, final, count),
    }


def main():
    for r in REFUSED:
        try:
            d.draw(r["candidates"], bytes(32), r["count"])
        except d.Refused:
            continue
        raise SystemExit(f"the reference accepted a list it must refuse: {r['why']}")

    cases = [
        case("one host, one pick", ONE_HOST, SEED, ENTROPY, 1),
        case("one host, all of it", ONE_HOST, SEED, ENTROPY, len(ONE_HOST)),
        case("several hosts, three picks", MANY_HOSTS, SEED, ENTROPY, 3),
        case("several hosts, all of it", MANY_HOSTS, SEED, ENTROPY, len(MANY_HOSTS)),
        case("another seed", MANY_HOSTS, OTHER_SEED, ENTROPY, 3),
        case("the same list, reordered", list(reversed(MANY_HOSTS)), SEED, ENTROPY, 3),
        case("one service spelt three ways is one host", SAME_SERVICE_SPELT_DIFFERENTLY, SEED, ENTROPY, 4),
        case("the cap is reached and the draw is shorter", CAP_REACHED, SEED, ENTROPY, len(CAP_REACHED)),
    ]
    out = {
        "version": "0.1.0",
        "hosts": {c: d.host_of(c) for c in HOSTS},
        "cases": cases,
        "refused": REFUSED,
    }
    capped = cases[-1]
    assert len(capped["picks"]) < capped["count"], "the cap case must actually reach the cap"
    path = Path(__file__).parent.parent / "vectors" / "draw.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="ascii")
    print(f"wrote {path}: {len(cases)} cases, {len(REFUSED)} refusals, cap case drew {len(capped['picks'])} of {capped['count']}")


if __name__ == "__main__":
    main()
