# Sasona protocol

The rules every Sasona implementation follows.

A member's software and ours have to reach the same answer from the same inputs: the same draw from the same seed, the same hash for the same answer, the same ranking from the same prices. This repository writes those rules down precisely enough that someone who has never seen our code can build their own and check it against ours.

Each rule comes with test values. If your implementation produces them, it agrees with the network.

> Nothing is specified yet. The first rules arrive with part 2 of the [roadmap](https://github.com/sasona-network/roadmap).

## Versions

The protocol is versioned. A change that makes two implementations disagree is a new major version.
