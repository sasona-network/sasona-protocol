"""Write vectors/chargeback.json from the reference implementation.

    python make_chargeback_vectors.py

Every expected value is written here by hand and checked against the
reference, not taken from what it prints.
"""

import hashlib
import json
from pathlib import Path

import chargeback as cb
import reader as rd

SERVICE = "https://sandbox.example.net/run/python"
COMMITTED = 1_000


def seated(keys, since=None):
    since = since or {}
    return [{"key": k, "since": since.get(i + 1, COMMITTED - 100), "member": 21 + 3 * i} for i, k in enumerate(keys)]


def main():
    amounts = [
        # price, rate, premium, fee, counted
        (1_000_000, 150, 15_000, 50_000, 1_050_000),
        (1_000_000, 1, 100, 50_000, 1_050_000),
        (19, 150, 0, 0, 19),
        (100_000, 10_000, 100_000, 5_000, 105_000),
    ]
    amount_cases = []
    for price, rate, prem, f, c in amounts:
        assert (cb.premium(price, rate), cb.fee(price), cb.counted(price)) == (prem, f, c), price
        amount_cases.append({"price": price, "rate": rate, "premium": prem, "fee": f, "counted": c})

    rooms = [
        # stake, usd_reserve, coin_reserve, open, owed, room
        ("a fresh stake at 5,000 coins a dollar", 10_000_000_000, 1_000_000, 5_000_000_000, 0, 0, 2_000_000),
        ("less what open purchases could cost", 10_000_000_000, 1_000_000, 5_000_000_000, 1_050_000, 0, 950_000),
        ("less what is owed, rounded up", 10_000_000_000, 1_000_000, 5_000_000_000, 0, 5_001, 1_999_998),
        ("a higher price gives more room", 10_000_000_000, 2_000_000, 5_000_000_000, 0, 0, 4_000_000),
    ]
    room_cases = []
    for name, stake, usd, coins, open_total, owed, want in rooms:
        got = cb.room(stake, usd, coins, open_total, owed)
        assert got == want, (name, got, want)
        room_cases.append({"name": name, "stake": stake, "usd_reserve": usd, "coin_reserve": coins,
                           "open": open_total, "owed": owed, "room": got})

    settles = [
        # name, price, deposit, verdict, (to buyer, deposit back, deposit to replayer, fee from cover, owed)
        ("delivers, deposit paid", 1_000_000, 50_000, 1, (0, 0, 50_000, 0, 0)),
        ("delivers, first chargeback", 1_000_000, 0, 1, (0, 0, 0, 50_000, 50_000)),
        ("does not deliver, deposit paid", 1_000_000, 50_000, 2, (1_000_000, 50_000, 0, 50_000, 1_050_000)),
        ("empty, first chargeback", 1_000_000, 0, 3, (1_000_000, 0, 0, 50_000, 1_050_000)),
        ("never happens", 1_000_000, 50_000, None, (1_000_000, 50_000, 0, 0, 1_000_000)),
    ]
    settle_cases = []
    for name, price, deposit, verdict, want in settles:
        got = cb.settle(price, deposit, verdict)
        assert got == want, (name, got, want)
        settle_cases.append({"name": name, "price": price, "deposit": deposit, "verdict": verdict,
                             "to_buyer": got[0], "deposit_back": got[1], "deposit_to_replayer": got[2],
                             "fee_from_cover": got[3], "owed": got[4]})

    chargeback_id = hashlib.sha256(b"a chargeback").digest()
    entropy = hashlib.sha256(b"a slot hash").digest()
    seed0 = cb.replay_seed(chargeback_id, 0, entropy)
    seed1 = cb.replay_seed(chargeback_id, 1, entropy)
    assert seed0 == hashlib.sha256(b"sasona/replay/v1" + chargeback_id + b"\x00\x00\x00\x00" + entropy).digest()
    five = ["A", "B", "C", "D", "E"]
    draws0 = [rd.s(seed0, SERVICE, a, 5) for a in range(rd.MAX_ATTEMPTS)]
    first = draws0[0]
    second = next(k for k in draws0 if k != first)
    seats = [
        ("no one passed over", seated(five), set(), set(), first),
        ("the buyer's key holds the first seat drawn", seated(five), {five[first - 1]}, set(), second),
        ("the membership in the first seat drawn declined before", seated(five), set(), {21 + 3 * (first - 1)}, second),
        ("a seat whose number is a declined membership's is not passed over", seated(five), set(), {first}, first),
        ("the first seat drawn was sat in since", seated(five, {first: COMMITTED + 1}), set(), set(), second),
        ("everyone passed over", seated(five), set(five), set(), None),
    ]
    seat_cases = []
    for name, ss, keys, declined, want in seats:
        got = cb.replay_seat(seed0, SERVICE, 5, COMMITTED, ss, keys, declined)
        assert got == want, (name, got, want)
        seat_cases.append({"name": name, "seats": ss, "passed_over_keys": sorted(keys), "declined": sorted(declined),
                           "seat": got})

    out = {
        "version": "0.7.0",
        "amounts": amount_cases,
        "rooms": room_cases,
        "settlements": settle_cases,
        "replay": {"chargeback": chargeback_id.hex(), "entropy": entropy.hex(), "service": SERVICE,
                   "members": 5, "committed_slot": COMMITTED,
                   "seeds": [seed0.hex(), seed1.hex()], "draws": draws0, "seats": seat_cases},
    }
    path = Path(__file__).parent.parent / "vectors" / "chargeback.json"
    path.write_bytes((json.dumps(out, indent=1) + "\n").encode("ascii"))
    print(f"wrote {path}: draws {draws0[:4]}, first {first}, then {second}")


if __name__ == "__main__":
    main()
