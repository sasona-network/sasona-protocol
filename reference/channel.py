"""Payment channels and the markup, as SPEC.md section 8 defines them. Standard library only."""

import hashlib

MARKUP_POINTS = 15
NOTICE_SLOTS = 648_000
VOUCHER_DOMAIN = b"sasona/voucher/v1"
DEVNET = 1


def markup(price: int) -> int:
    """8.1: 15% of the price, rounded up."""
    return -(-MARKUP_POINTS * price // 100)


def payable(voucher: int, put_in: int) -> int:
    """8.4: the most a channel holding `put_in` can pay on a voucher: the
    largest x, at most the voucher, with x + markup(x) within put_in."""
    return min(voucher, 100 * put_in // (100 + MARKUP_POINTS))


def voucher_message(program: bytes, cluster: int, channel: bytes, amount: int) -> bytes:
    """8.3: the 90 bytes the signer signs."""
    assert len(program) == 32 and len(channel) == 32 and 0 <= cluster < 256
    return VOUCHER_DOMAIN + program + bytes([cluster]) + channel + amount.to_bytes(8, "big")


class Refused(Exception):
    pass


class Channel:
    """8.2 to 8.5, as the program keeps it. `balance` is what its token
    account holds, which can be more than the record if someone sent dollars
    to it."""

    def __init__(self, put_in: int):
        self.put_in = put_in
        self.balance = put_in
        self.taken = 0
        self.charged = 0
        self.owed = 0
        self.asked = None

    def _open_at(self, slot):
        return self.asked is None or slot < self.asked + NOTICE_SLOTS

    def add(self, amount, slot):
        if self.asked is not None:
            raise Refused("a close is pending")
        self.put_in += amount
        self.balance += amount

    def donate(self, amount):
        self.balance += amount

    def pay(self, voucher, slot):
        """Returns (to the payee, markup charged)."""
        if not self._open_at(slot):
            raise Refused("the notice is over")
        x = payable(voucher, self.put_in)
        if x <= self.taken:
            raise Refused("nothing more to pay")
        to_payee = x - self.taken
        charge = markup(x) - self.charged
        self.taken, self.charged, self.owed = x, self.charged + charge, self.owed + charge
        self.balance -= to_payee
        self._check()
        return to_payee, charge

    def sweep(self):
        """Returns the markup moved to the network."""
        if self.owed == 0:
            raise Refused("nothing owed")
        moved, self.owed = self.owed, 0
        self.balance -= moved
        self._check()
        return moved

    def ask_to_close(self, slot):
        if self.asked is not None:
            raise Refused("already asked")
        self.asked = slot

    def close(self, slot, by_payee: bool):
        """Returns (markup to the network, back to the payer)."""
        if not by_payee and (self.asked is None or slot < self.asked + NOTICE_SLOTS):
            raise Refused("the notice is not over")
        out = (self.owed, self.balance - self.owed)
        self.balance = 0
        return out

    def _check(self):
        assert self.taken + self.charged <= self.put_in
        assert self.balance >= self.put_in - self.taken - (self.charged - self.owed)


# ------------------------------------------------------------- ed25519
#
# RFC 8032, section 6, so that a voucher can be signed and checked here with
# nothing installed. Slow, and not safe against timing attacks: for test
# values only, never for a key that holds anything.

_p = 2**255 - 19
_d = -121665 * pow(121666, _p - 2, _p) % _p
_q = 2**252 + 27742317777372353535851937790883648493


def _sha512(b):
    return hashlib.sha512(b).digest()


def _add(P, Q):
    A, B = (P[1] - P[0]) * (Q[1] - Q[0]) % _p, (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C, D = 2 * P[3] * Q[3] * _d % _p, 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _equal(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % _p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


_modp_sqrt_m1 = pow(2, (_p - 1) // 4, _p)


def _recover_x(y, sign):
    if y >= _p:
        return None
    x2 = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p != 0:
        x = x * _modp_sqrt_m1 % _p
    if (x * x - x2) % _p != 0:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


_gy = 4 * pow(5, _p - 2, _p) % _p
_gx = _recover_x(_gy, 0)
_G = (_gx, _gy, 1, _gx * _gy % _p)


def _compress(P):
    zinv = pow(P[2], _p - 2, _p)
    x, y = P[0] * zinv % _p, P[1] * zinv % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _p)


def _expand(secret):
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    a, _ = _expand(secret)
    return _compress(_mul(a, _G))


def sign(secret: bytes, message: bytes) -> bytes:
    a, prefix = _expand(secret)
    A = _compress(_mul(a, _G))
    r = int.from_bytes(_sha512(prefix + message), "little") % _q
    R = _compress(_mul(r, _G))
    h = int.from_bytes(_sha512(R + A + message), "little") % _q
    return R + int.to_bytes((r + h * a) % _q, 32, "little")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    if len(public) != 32 or len(signature) != 64:
        return False
    A = _decompress(public)
    R = _decompress(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if A is None or R is None or s >= _q:
        return False
    h = int.from_bytes(_sha512(signature[:32] + public + message), "little") % _q
    return _equal(_mul(s, _G), _add(R, _mul(h, A)))
