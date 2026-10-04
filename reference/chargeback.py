"""Purchases and chargebacks, as SPEC.md section 7 defines them. Standard library only."""

import hashlib

from reader import MAX_ATTEMPTS, s

REPLAY_DOMAIN = b"sasona/replay/v1"
FEE_BPS = 500


def premium(price: int, rate: int) -> int:
    """7.2: the price times the rate in basis points, over 10,000, rounded down."""
    return price * rate // 10_000


def fee(price: int) -> int:
    """7.4: the replayer's pay, and the deposit: 5% of the price, rounded down."""
    return price * FEE_BPS // 10_000


def counted(price: int) -> int:
    """7.2: what an open purchase could cost its member."""
    return price + fee(price)


def room(stake: int, usd_reserve: int, coin_reserve: int, open_total: int, owed: int) -> int:
    """7.2: a member's room to insure, in dollar units: the stake valued at the
    pool's price, less what open purchases could cost, less what is owed,
    valued the same way. Values round down, and owing rounds up."""
    stake_usd = stake * usd_reserve // coin_reserve
    owed_usd = -(-owed * usd_reserve // coin_reserve)
    return stake_usd - open_total - owed_usd


def replay_seed(chargeback: bytes, draw: int, entropy: bytes) -> bytes:
    """7.4: the seed a replay's seat is drawn with."""
    assert len(chargeback) == 32 and len(entropy) == 32
    return hashlib.sha256(REPLAY_DOMAIN + chargeback + draw.to_bytes(4, "big") + entropy).digest()


def replay_seat(seed: bytes, service: str, members: int, committed_slot: int, seats: list,
                passed_over_keys: set, declined: set):
    """7.4: the seat drawn to replay, or None.

    As 4.3, with `seats` as in reader.reader, each also naming the
    membership in it, and also passing over every seat held by a key in
    `passed_over_keys` (the buyer's and the quoter's) and every seat whose
    membership is in `declined`. Seats move when members leave, so a decline
    is the membership's, not the seat's."""
    if members == 0:
        return None
    for attempt in range(MAX_ATTEMPTS):
        k = s(seed, service, attempt, members)
        if k > len(seats):
            continue
        seat = seats[k - 1]
        if seat["since"] < committed_slot and seat["key"] not in passed_over_keys and seat["member"] not in declined:
            return k
    return None


def settle(price: int, deposit: int, verdict):
    """7.5: who gets what, in dollar units. `verdict` is the replay's, or None
    if it never happened. Returns (to_buyer_from_cover, deposit_to_buyer,
    deposit_to_replayer, fee_from_cover, owed_by_quoter_in_dollars)."""
    f = fee(price)
    if verdict == 1:
        if deposit:
            return 0, 0, deposit, 0, 0
        return 0, 0, 0, f, f
    replayed = verdict is not None
    from_cover_fee = f if replayed else 0
    return price, deposit, 0, from_cover_fee, price + from_cover_fee
