"""Write vectors/channel.json from the reference implementation.

    python make_channel_vectors.py

Every expected value is written here by hand and checked against the
reference, not taken from what it prints.
"""

import hashlib
import json
import os
from pathlib import Path

import channel as ch

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + ALPHABET.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\0" * (len(s) - len(s.lstrip("1"))) + raw


PROGRAM = "7eiHSnDkM4WjJdY36D2Yqsjw893mCMUtBAwMCQ5adL99"
# A key made for this file and thrown away: only its public half and one
# signature are written down.
SIGNER_SECRET = os.urandom(32)


def main():
    markups = [(0, 0), (1, 1), (7, 2), (20, 3), (100_000, 15_000), (1_000_000, 150_000), (100_007, 15_002)]
    for price, want in markups:
        assert ch.markup(price) == want, price

    payables = [
        # voucher, put in, payable
        ("the channel covers it", 50, 100, 50),
        ("exactly a dollar and its markup", 2_000_000, 1_150_000, 1_000_000),
        ("one unit short of that", 2_000_000, 1_149_999, 999_999),
        ("too little for anything", 1, 1, 0),
    ]
    for name, v, d, want in payables:
        assert ch.payable(v, d) == want, name
        assert want + ch.markup(want) <= d, name
        assert want == v or (want + 1) + ch.markup(want + 1) > d, name

    program = b58decode(PROGRAM)
    channel = hashlib.sha256(b"a channel").digest()
    message = ch.voucher_message(program, ch.DEVNET, channel, 100_007)
    assert len(message) == 90
    assert message == b"sasona/voucher/v1" + program + b"\x01" + channel + bytes([0, 0, 0, 0, 0, 1, 0x86, 0xA7])
    public = ch.public_key(SIGNER_SECRET)
    signature = ch.sign(SIGNER_SECRET, message)
    assert ch.verify(public, message, signature)
    other = ch.voucher_message(program, 2, channel, 100_007)
    assert not ch.verify(public, other, signature)

    # A channel through its life. Each step: what it does, and what must come out.
    steps = [
        ("open with $1", ("open", 1_000_000), None),
        ("pay a voucher of 100,000", ("pay", 100_000, 10), [100_000, 15_000]),
        ("pay 100,007: 7 more, and the markup on the total less what was charged", ("pay", 100_007, 11), [7, 2]),
        ("the same voucher again", ("pay", 100_007, 12), "refused"),
        ("sweep the markup owed", ("sweep",), 15_002),
        ("sweep with nothing owed", ("sweep",), "refused"),
        ("a voucher larger than the channel can pay pays what it can", ("pay", 900_000, 13), [769_558, 115_433]),
        ("someone sends 10 units to the channel's account", ("donate", 10), None),
        ("the payee closes", ("close", 14, True), [115_433, 10]),
    ]
    c = None
    recorded = []
    for name, op, want in steps:
        kind = op[0]
        try:
            if kind == "open":
                c = ch.Channel(op[1])
                got = None
            elif kind == "pay":
                got = list(c.pay(op[1], op[2]))
            elif kind == "sweep":
                got = c.sweep()
            elif kind == "donate":
                got = c.donate(op[1])
            elif kind == "close":
                got = list(c.close(op[1], op[2]))
        except ch.Refused:
            got = "refused"
        assert got == want, (name, got, want)
        recorded.append({"name": name, "op": list(op), "result": want})
    assert c.taken + c.charged == 1_000_000

    asked = 5_000_000
    end = asked + ch.NOTICE_SLOTS
    notice = [
        ("pay on the last slot of the notice", ("pay", end - 1), True),
        ("pay on the slot the notice ends", ("pay", end), False),
        ("finish on the last slot of the notice", ("finish", end - 1), False),
        ("finish on the slot the notice ends", ("finish", end), True),
        ("add during the notice", ("add", asked + 1), False),
        ("ask to close a second time", ("ask", asked + 1), False),
    ]
    notice_cases = []
    for name, (kind, slot), allowed in notice:
        c = ch.Channel(1_000_000)
        c.ask_to_close(asked)
        try:
            if kind == "pay":
                c.pay(1_000, slot)
            elif kind == "finish":
                c.close(slot, by_payee=False)
            elif kind == "add":
                c.add(1, slot)
            elif kind == "ask":
                c.ask_to_close(slot)
            ok = True
        except ch.Refused:
            ok = False
        assert ok == allowed, name
        notice_cases.append({"name": name, "op": kind, "slot": slot, "allowed": allowed})

    out = {
        "version": "0.8.0",
        "markups": [{"price": p, "markup": m} for p, m in markups],
        "payables": [{"name": n, "voucher": v, "put_in": d, "payable": x} for n, v, d, x in payables],
        "voucher": {
            "program": PROGRAM, "cluster": ch.DEVNET, "channel": channel.hex(), "amount": 100_007,
            "message": message.hex(), "signer": public.hex(),
            "signature": signature.hex(), "message_for_cluster_2": other.hex(),
        },
        "life": recorded,
        "notice": {"asked": asked, "notice_slots": ch.NOTICE_SLOTS, "put_in": 1_000_000, "voucher": 1_000,
                   "cases": notice_cases},
    }
    path = Path(__file__).parent.parent / "vectors" / "channel.json"
    path.write_bytes((json.dumps(out, indent=1) + "\n").encode("ascii"))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
