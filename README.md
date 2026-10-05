# Sasona protocol

The rules every Sasona implementation follows.

A member's software and ours have to reach the same answer from the same inputs: the same draw from the same seed, the same hash for the same answer, the same ranking from the same prices. This repository writes those rules down precisely enough that someone who has never seen our code can build their own and check it against ours.

## What is specified

| Version | What it covers |
|---|---|
| [0.8.0](SPEC.md) | Section 1, the draw: how a round's seed and its list of services decide which services get tested, so anyone can re-run it |
| | Section 2, the question: how a member tests a drawn service so the test is fixed before the service replies, and the verdict can be checked afterwards |
| | Section 3, second readings: which reading is tested again, by whom, and what the two together settle |
| | Section 4, members: a stake per membership, a roster of seats, and drawing the member who reads each service |
| | Section 5, challenges: a member shows the reply behind a reading, or loses the stake |
| | Section 6, the ranking: services ranked by the lowest price a member who read them would insure them at |
| | Section 7, chargebacks: a covered purchase, a replay by a member drawn for it, and who pays the buyer back |
| | Section 8, payment channels: an agent's dollars held by the program, paid to the node that buys for it against vouchers the agent signs, with the markup every purchase carries |

## Check an implementation

[`vectors/`](vectors/) holds fixed inputs, one file per section, with the results every implementation must produce and the inputs it must refuse. Two implementations, in two languages, each written from the specification, match it:

```bash
python reference/check.py           # Python, standard library only
cd rust && cargo test               # Rust
```

Both are ours. An implementation written by somebody else is what really tests a specification, and if yours produces the same values, it agrees with the network.

## Versions

A change that makes two implementations disagree is a new major version.
