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

import question as q  # noqa: E402

Q = json.loads((Path(__file__).parent.parent / "vectors" / "question.json").read_text(encoding="ascii"))
for c in Q["questions"]:
    qu = q.question(c["nonce"])
    check(f"question {c['nonce'][:8]}…: expected answer", qu["expect"] == c["expect"])
    check(f"question {c['nonce'][:8]}…: code", qu["code"] == c["code"])
    check(f"question {c['nonce'][:8]}…: canonical form", q.canonical(c["nonce"]).decode() == c["canonical"])
    check(f"question {c['nonce'][:8]}…: hash", q.question_hash(c["nonce"]).hex() == c["question_hash"])
for b in Q["bad_nonces"]:
    try:
        q.canonical(b["nonce"])
        check(f"refuses a nonce: {b['why']}", False)
    except ValueError:
        check(f"refuses a nonce: {b['why']}", True)
nonce = Q["verdicts"]["nonce"]
for r in Q["verdicts"]["replies"]:
    reply = bytes.fromhex(r["reply_hex"])
    check(f"reply '{r['name']}': hash", q.reply_hash(reply).hex() == r["reply_hash"])
    check(f"reply '{r['name']}': {r['verdict_name']}", q.verdict(reply, nonce) == r["verdict"])
check("the fair question is fair", q.is_fair(Q["fair"].encode()))
for u in Q["unfair"]:
    check(f"refuses as unfair: {u['name']}", not q.is_fair(u["bytes"].encode()))

import pair as pr  # noqa: E402

PV = json.loads((Path(__file__).parent.parent / "vectors" / "pair.json").read_text(encoding="ascii"))
for o in PV["outcomes"]:
    check(f"pair {o['first_name']} then {o['second_name']}: {o['outcome_name']}", pr.outcome(o["first"], o["second"]) == o["outcome"])
for c in PV["counting"]:
    args = {k: c[k] for k in ("first_reader", "second_reader", "first_revealed_slot", "round_committed_slot", "same_service", "same_round", "first_is_latest")}
    check(f"second reading {'counts' if c['counts'] else 'does not count'}: {c['name']}", pr.counts(**args) == c["counts"])
for c in PV["latest"]:
    check(f"latest reading: {c['name']}", pr.latest(c["readings"], c["round_committed_slot"]) == c["latest"])

import reader as rd  # noqa: E402

RV = json.loads((Path(__file__).parent.parent / "vectors" / "reader.json").read_text(encoding="ascii"))
check("reader: at most 16 attempts", RV["max_attempts"] == rd.MAX_ATTEMPTS)
for c in RV["cases"]:
    f = bytes.fromhex(c["final_seed"])
    m = c["members"]
    draws = [rd.s(f, c["service"], a, m) for a in range(rd.MAX_ATTEMPTS)] if m else []
    check(f"reader: {c['name']}: the draws", draws == c["attempts"])
    check(f"reader: {c['name']}: seat {c['reader']}", rd.reader(f, c["service"], m, c["committed_slot"], c["seats"], c["first_reader"]) == c["reader"])

import ranking as rk  # noqa: E402

KV = json.loads((Path(__file__).parent.parent / "vectors" / "ranking.json").read_text(encoding="ascii"))
check("ranking: a reading is current for 30 days", KV["term_seconds"] == rk.TERM_SECONDS)
for c in KV["standing"]:
    check(f"quote {'stands' if c['stands'] else 'does not stand'}: {c['name']}", rk.stands(c["quote"], c["at"]) == c["stands"])
for c in KV["rankings"]:
    check(f"ranking: {c['name']}", [list(x) for x in rk.rank(c["services"], c["at"])] == c["ranking"])

print()
print(f"{failures} failed" if failures else "all vectors match")
sys.exit(1 if failures else 0)
