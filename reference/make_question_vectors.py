"""Write vectors/question.json from the reference implementation.

    python make_question_vectors.py
"""

import json
from pathlib import Path

import question as q

NONCES = ["0123456789abcdef0123456789abcdef", "ffffffffffffffffffffffffffffffff", "9a3e5c0d71b24f68aa0b1c2d3e4f5061"]
BAD_NONCES = [
    ("31 characters", "0123456789abcdef0123456789abcde"),
    ("33 characters", "0123456789abcdef0123456789abcdef0"),
    ("not hex", "0123456789abcdef0123456789abcdeg"),
    ("uppercase", "0123456789ABCDEF0123456789ABCDEF"),
]


def main():
    cases = [
        {"nonce": n, "expect": q.expected(n), "code": q.code_for(n),
         "canonical": q.canonical(n).decode("ascii"), "question_hash": q.question_hash(n).hex()}
        for n in NONCES
    ]

    n0 = NONCES[0]
    e = q.expected(n0).encode()
    replies = [
        ("the answer and nothing else", e + b"\n"),
        ("the answer inside JSON", json.dumps({"stdout": e.decode() + "\n", "exit": 0}).encode()),
        ("the answer between bytes that are not text", b"\xff\x00" + e + b"\xfe"),
        ("the answer inside a longer run of hex", b"00" + e + b"ff"),
        ("an echo of the code that was sent", q.code_for(n0).encode()),
        ("an echo of the question, which must never be sent", q.canonical(n0)),
        ("a canned reply", b'{"status":"ok","output":"done"}'),
        ("the answer in capitals", e.upper()),
        ("the answer broken by a newline", e[:8] + b"\n" + e[8:]),
        ("fifteen of the sixteen characters", e[:15]),
        ("nothing", b""),
    ]
    verdicts = [
        {"name": name, "reply_hex": r.hex(), "reply_hash": q.reply_hash(r).hex(),
         "verdict": q.verdict(r, n0), "verdict_name": q.VERDICTS[q.verdict(r, n0)]}
        for name, r in replies
    ]

    fair = q.canonical(n0).decode("ascii")
    obj = q.question(n0)

    def variant(**changes):
        d = json.loads(json.dumps(obj))
        for k, v in changes.items():
            if v is None:
                d.pop(k)
            else:
                d[k] = v
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    unfair = [
        ("a different expected answer", variant(expect="0" * 16)),
        ("the tier as true", variant(tier=True)),
        ("the tier as 1.0", variant(tier=1.0)),
        ("the tier as a string", variant(tier="1")),
        ("a key added", variant(extra=1)),
        ("a key missing", variant(command=None)),
        ("the code changed in one shape only", variant(body={"code": "print(1)", "language": "python"})),
        ("the same object with spaces", json.dumps(obj, sort_keys=True)),
        ("the same object, keys in another order", json.dumps(obj, separators=(",", ":"))),
    ]
    assert all(not q.is_fair(s.encode()) for _, s in unfair)
    assert q.is_fair(fair.encode())

    out = {
        "version": "0.3.0",
        "questions": cases,
        "bad_nonces": [{"why": w, "nonce": n} for w, n in BAD_NONCES],
        "verdicts": {"nonce": n0, "replies": verdicts},
        "fair": fair,
        "unfair": [{"name": name, "bytes": s} for name, s in unfair],
    }
    path = Path(__file__).parent.parent / "vectors" / "question.json"
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="ascii", newline="\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
