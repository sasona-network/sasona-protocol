# Sasona protocol

The rules every Sasona implementation follows.

A member's software and ours have to reach the same answer from the same inputs: the same draw from the same seed, the same hash for the same answer, the same ranking from the same prices. This repository writes those rules down precisely enough that someone who has never seen our code can build their own and check it against ours.

## What is specified

| Version | What it covers |
|---|---|
| [0.2.0](SPEC.md) | The draw: how a round's seed and its list of services decide which services get tested, so anyone can re-run it, and why a list can be drawn only once |

## Check an implementation

[`vectors/draw.json`](vectors/draw.json) holds fixed inputs, the results every implementation must produce, and lists every implementation must refuse. Two implementations, in two languages, each written from the specification, match it:

```bash
python reference/check.py           # Python, standard library only
cd rust && cargo test               # Rust
```

Both are ours. An implementation written by somebody else is what really tests a specification, and if yours produces the same values, it agrees with the network.

## Versions

A change that makes two implementations disagree is a new major version.
