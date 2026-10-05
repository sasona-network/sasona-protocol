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
for c in KV["premiums"]:
    check(f"premium: {c['name']}: {c['premium']}", rk.premium(c["readings"], c["now"]) == c["premium"])
for c in KV["rankings"]:
    check(f"ranking: {c['name']}", [list(x) for x in rk.rank(c["services"], c["now"])] == c["ranking"])

import chargeback as cb  # noqa: E402

CV = json.loads((Path(__file__).parent.parent / "vectors" / "chargeback.json").read_text(encoding="ascii"))
for c in CV["amounts"]:
    check(f"chargeback: price {c['price']} at {c['rate']} bps",
          (cb.premium(c["price"], c["rate"]), cb.fee(c["price"]), cb.counted(c["price"])) == (c["premium"], c["fee"], c["counted"]))
for c in CV["rooms"]:
    check(f"room to insure: {c['name']}", cb.room(c["stake"], c["usd_reserve"], c["coin_reserve"], c["open"], c["owed"]) == c["room"])
for c in CV["settlements"]:
    want = (c["to_buyer"], c["deposit_back"], c["deposit_to_replayer"], c["fee_from_cover"], c["owed"])
    check(f"settlement: {c['name']}", cb.settle(c["price"], c["deposit"], c["verdict"]) == want)
R = CV["replay"]
ident, entropy = bytes.fromhex(R["chargeback"]), bytes.fromhex(R["entropy"])
check("replay: the seeds", [cb.replay_seed(ident, d, entropy).hex() for d in (0, 1)] == R["seeds"])
check("replay: the draws", [rd.s(bytes.fromhex(R["seeds"][0]), R["service"], a, R["members"]) for a in range(rd.MAX_ATTEMPTS)] == R["draws"])
for c in R["seats"]:
    got = cb.replay_seat(bytes.fromhex(R["seeds"][0]), R["service"], R["members"], R["committed_slot"], c["seats"],
                         set(c["passed_over_keys"]), set(c["declined"]))
    check(f"replay seat: {c['name']}", got == c["seat"])


import channel as ch  # noqa: E402

for c in CV["amounts"]:
    check(f"markup on a covered purchase of {c['price']}", ch.markup(c["price"]) == c["markup"])
HV = json.loads((Path(__file__).parent.parent / "vectors" / "channel.json").read_text(encoding="ascii"))
for c in HV["markups"]:
    check(f"markup on {c['price']}", ch.markup(c["price"]) == c["markup"])
for c in HV["payables"]:
    check(f"payable: {c['name']}", ch.payable(c["voucher"], c["put_in"]) == c["payable"])
W = HV["voucher"]
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
n = 0
for ch_ in W["program"]:
    n = n * 58 + ALPHA.index(ch_)
program = n.to_bytes(32, "big")
message = ch.voucher_message(program, W["cluster"], bytes.fromhex(W["channel"]), W["amount"])
check("voucher: the 90 bytes signed", message.hex() == W["message"] and len(message) == 90)
check("voucher: it verifies", ch.verify(bytes.fromhex(W["signer"]), message, bytes.fromhex(W["signature"])))
check("voucher: it does not verify for another cluster",
      not ch.verify(bytes.fromhex(W["signer"]), bytes.fromhex(W["message_for_cluster_2"]), bytes.fromhex(W["signature"])))
life = None
for s in HV["life"]:
    op = s["op"]
    try:
        if op[0] == "open":
            life = ch.Channel(op[1])
            got = None
        elif op[0] == "pay":
            got = list(life.pay(op[1], op[2]))
        elif op[0] == "sweep":
            got = life.sweep()
        elif op[0] == "donate":
            got = life.donate(op[1])
        elif op[0] == "close":
            got = list(life.close(op[1], op[2]))
    except ch.Refused:
        got = "refused"
    check(f"channel: {s['name']}", got == s["result"])
N = HV["notice"]
for c in N["cases"]:
    k = ch.Channel(N["put_in"])
    k.ask_to_close(N["asked"])
    try:
        if c["op"] == "pay":
            k.pay(N["voucher"], c["slot"])
        elif c["op"] == "finish":
            k.close(c["slot"], by_payee=False)
        elif c["op"] == "add":
            k.add(1, c["slot"])
        elif c["op"] == "ask":
            k.ask_to_close(c["slot"])
        ok = True
    except ch.Refused:
        ok = False
    check(f"notice: {c['name']}", ok == c["allowed"])

print()
print(f"{failures} failed" if failures else "all vectors match")
sys.exit(1 if failures else 0)
