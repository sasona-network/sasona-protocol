"""The Sasona draw, as SPEC.md section 1 defines it. Standard library only.

    python draw.py <candidates file> <final seed, hex> <count>

prints the picks, one per line. The candidates file has one URL per line,
in the round's order; surrounding whitespace on a line is ignored.
"""

import hashlib
import hmac
import sys

DOMAIN = b"sasona/draw/v1"
ATTEMPTS_PER_CANDIDATE = 64
MAX_CANDIDATES = 65_536


class Refused(ValueError):
    """A list or count the spec says to reject."""


def host_of(candidate: str) -> str:
    """SPEC.md 1.1. Raises Refused for a candidate that is not allowed."""
    if not candidate or any(not 0x21 <= ord(ch) <= 0x7E for ch in candidate):
        raise Refused(f"not printable ASCII: {candidate!r}")
    scheme, sep, rest = candidate.partition("://")
    scheme = scheme.lower()
    if not sep or scheme not in ("http", "https"):
        raise Refused(f"not http or https: {candidate!r}")
    for stop in "/?#":
        rest = rest.split(stop, 1)[0]
    rest = rest.rsplit("@", 1)[-1]
    host = "".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in rest)
    default = ":443" if scheme == "https" else ":80"
    if host.endswith(default):
        host = host[: -len(default)]
    if host.endswith("."):
        host = host[:-1]
    if not host:
        raise Refused(f"no host: {candidate!r}")
    return host


def pool_fingerprint(candidates: list[str]) -> bytes:
    h = hashlib.sha256()
    for c in candidates:
        h.update(c.encode("ascii"))
        h.update(b"\x00")
    return h.digest()


def seed_hash(seed: bytes) -> bytes:
    assert len(seed) == 32
    return hashlib.sha256(seed).digest()


def final_seed(seed: bytes, entropy: bytes) -> bytes:
    assert len(seed) == 32 and len(entropy) == 32
    return hashlib.sha256(DOMAIN + seed + entropy).digest()


def _r(key: bytes, label: bytes, attempt: int) -> int:
    digest = hmac.new(key, label + attempt.to_bytes(4, "big"), hashlib.sha256).digest()
    return int.from_bytes(digest, "big")


def draw(candidates: list[str], final: bytes, count: int) -> list[str]:
    if not 0 < len(candidates) <= MAX_CANDIDATES:
        raise Refused("a list holds between 1 and 65,536 candidates")
    if len(set(candidates)) != len(candidates):
        raise Refused("a candidate appears twice")
    if not 0 < count <= len(candidates):
        raise Refused("count must be between 1 and the number of candidates")

    hosts: list[str] = []
    endpoints: dict[str, list[str]] = {}
    for c in candidates:
        h = host_of(c)
        if h not in endpoints:
            hosts.append(h)
            endpoints[h] = []
        endpoints[h].append(c)

    picked: list[str] = []
    attempt = 0
    while len(picked) < count and attempt < ATTEMPTS_PER_CANDIDATE * len(candidates):
        host = hosts[_r(final, b"host", attempt) % len(hosts)]
        options = endpoints[host]
        candidate = options[_r(final, b"endpoint", attempt) % len(options)]
        if candidate not in picked:
            picked.append(candidate)
        attempt += 1
    return picked


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="ascii") as f:
        pool = [line.strip() for line in f if line.strip()]
    for p in draw(pool, bytes.fromhex(sys.argv[2]), int(sys.argv[3])):
        print(p)
