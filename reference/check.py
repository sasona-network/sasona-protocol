"""Check the reference implementation against vectors/draw.json.

    python check.py
"""

import json
import sys
from pathlib import Path

import draw as d

V = json.loads((Path(__file__).parent.parent / "vectors" / "draw.json").read_text(encoding="ascii"))
failures = 0

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + ALPHABET.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\0" * (len(s) - len(s.lstrip("1"))) + raw


def check(what, ok):
    global failures
    print(("  ok    " if ok else "  FAIL  ") + what)
    failures += not ok


for url, host in V["hosts"].items():
    check(f"host of {url}", d.host_of(url) == host)

for c in V["cases"]:
    seed, entropy = bytes.fromhex(c["seed"]), bytes.fromhex(c["entropy"])
    final = d.final_seed(seed, entropy)
    check(f"{c['name']}: entropy is the base58 hash's bytes, in order", b58decode(c["entropy_base58"]) == entropy)
    check(f"{c['name']}: seed hash", d.seed_hash(seed).hex() == c["seed_hash"])
    check(f"{c['name']}: pool fingerprint", d.pool_fingerprint(c["candidates"]).hex() == c["pool_fingerprint"])
    check(f"{c['name']}: final seed", final.hex() == c["final_seed"])
    check(f"{c['name']}: picks", d.draw(c["candidates"], final, c["count"]) == c["picks"])

for r in V["refused"]:
    try:
        d.draw(r["candidates"], bytes(32), r["count"])
        check(f"refuses: {r['why']}", False)
    except d.Refused:
        check(f"refuses: {r['why']}", True)

cases = {c["name"]: c for c in V["cases"]}
three, every = cases["several hosts, three picks"], cases["several hosts, all of it"]
check("a draw is a prefix of a longer one", every["picks"][:3] == three["picks"])
check("all of it means every candidate once", sorted(every["picks"]) == sorted(every["candidates"]))
check("reordering changes the fingerprint",
      cases["the same list, reordered"]["pool_fingerprint"] != three["pool_fingerprint"])
check("another seed gives another draw", cases["another seed"]["picks"] != three["picks"])
capped = cases["the cap is reached and the draw is shorter"]
check("the cap case is shorter than its count", len(capped["picks"]) < capped["count"])

print()
print(f"{failures} failed" if failures else "all vectors match")
sys.exit(1 if failures else 0)
