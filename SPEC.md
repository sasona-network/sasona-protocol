# Sasona protocol

**Version 0.1.0.** This version specifies one thing: the draw.

The words **MUST** and **MUST NOT** mark rules that change a result. An implementation that does otherwise computes different values from every other one and is not conformant.

## Versions

`MAJOR.MINOR.PATCH`. A change that alters a hash, a draw or any other computed value is a new major version. Anything an implementation hashes or draws **MUST** be recorded with the version it was made under.

---

## 1. The draw

Members test services, and they do not choose which. A round draws them from a list, using a seed nobody could control alone, and anybody can re-run the draw and get the same services.

### 1.1 Candidates

A candidate is a service's URL. A list holds at most **65,536** candidates.

A candidate **MUST** be made only of the bytes `0x21` to `0x7E` (printable ASCII, no spaces), **MUST** start with `http://` or `https://` (the scheme compared without regard to case), and its host, found as below, **MUST NOT** be empty. A list with any other candidate **MUST** be rejected, and so **MUST** a list that holds the same candidate twice. Candidates are compared exactly, byte for byte, so `https://a.example/x` and `https://A.example/x` are two different candidates on the same host.

A candidate's **host** is found like this, in order:

1. take the text after `://`
2. cut it at the first `/`, `?` or `#`
3. drop everything up to and including the last `@`
4. lowercase the ASCII letters `A` to `Z`, and nothing else
5. drop `:443` from an `https` URL and `:80` from an `http` URL, if the host ends with it
6. drop one trailing `.`, if there is one

| Candidate | Host |
|---|---|
| `https://Shop.Example.com/a` | `shop.example.com` |
| `https://user@shop.example.com:443/a` | `shop.example.com` |
| `http://shop.example.com.:80?q=1` | `shop.example.com` |
| `https://shop.example.com:8443/a` | `shop.example.com:8443` |
| `https://[::1]:443/x` | `[::1]` |

Order matters. It is fixed when the round is committed and is part of everything below.

### 1.2 The pool fingerprint

```
h = sha256()
for each candidate, in order:
    h.update(candidate bytes)
    h.update(0x00)
fingerprint = h.digest()
```

The `0x00` after each candidate is required. Without it, two lists that join to the same text would have the same fingerprint. The same candidates in a different order give a different fingerprint, because they give a different draw.

### 1.3 The commitment

The party opening a round picks 32 random bytes, the **seed**, and commits on chain, before anything else happens, to all of:

- the pool fingerprint
- the number of candidates
- **how many will be drawn**
- `sha256(seed)`

The count has to be fixed here. A draw is a prefix of every longer draw (1.6), so an opener who could choose the count after seeing the order could stop just before a service they did not want.

### 1.4 Outside entropy

The round is committed at a Solana slot, `commit_slot`. Its **target slot** is `commit_slot + 32`, a slot that did not exist when the round was committed. Solana can skip a slot, so the **entropy slot** is the earliest slot at or after the target slot that appears in the `SlotHashes` sysvar, and the **entropy** is the 32 bytes stored there for it, exactly as stored.

The program reads `SlotHashes` itself when the seed is revealed and records the entropy slot and the entropy with the round, so a verifier reads them from the round rather than looking them up.

`SlotHashes` holds the latest 512 entries, a few minutes. A round can be revealed only while it still reaches back to the target slot. After that it can only be marked **withheld**, and it can never be drawn.

### 1.5 The final seed

```
final_seed = sha256( "sasona/draw/v1"  ||  seed  ||  entropy )
```

`"sasona/draw/v1"` is the 14 bytes of that ASCII text. `seed` and `entropy` are 32 bytes each.

### 1.6 Selection

The hosts are the distinct hosts of the list, in order of their first appearance. Each host's endpoints are its candidates, in list order.

```
r(label, attempt) = int( HMAC-SHA256( key = final_seed,
                                      message = label || u32_be(attempt) ),
                         big-endian over all 32 bytes )

picked  = []
attempt = 0
while len(picked) < count and attempt < 64 * len(candidates):
    host      = hosts[ r("host", attempt) mod len(hosts) ]
    endpoints = endpoints_of(host)
    candidate = endpoints[ r("endpoint", attempt) mod len(endpoints) ]
    if candidate not in picked:
        picked.append(candidate)
    attempt += 1
```

Every detail of this changes the result:

- the key is the **final seed**, and the message is the **label then the attempt**
- the labels are the ASCII bytes `host` and `endpoint`
- the attempt is 4 bytes, big-endian. The 65,536-candidate limit keeps it below 2^32
- the digest is read as one big-endian integer
- a candidate already picked is **skipped**, never removed from the list, so every attempt is computed against the same list
- `count` **MUST** be at least 1 and **MUST NOT** exceed the number of candidates

The cap is `64 * len(candidates)` attempts. If it is reached, the draw is the picks so far, and that shorter list is the result of the round. It can happen when a few hosts hold most of the list.

Drawing `n` gives the first `n` of drawing `m > n`.

### 1.7 What the draw does and does not promise

- **Each attempt** picks every host with the same chance, so a host with thousands of listings is no likelier to be drawn on a given attempt than a host with one. Over several picks this does not hold: a host with one endpoint can be picked once, and later attempts that land on it are skipped.
- The host rules in 1.1 stop one service posing as several hosts through its spelling. They do not stop whoever builds the list from listing one business under many domains. What goes on a list is outside this version.
- The opener commits before the entropy exists, so they cannot aim the seed. After the entropy slot, they can compute the result before revealing and choose not to. That costs them the round's bond (see the program) and is recorded as withheld, but it is a choice they still have.
- Whoever produces the entropy slot does not know the seed. An opener colluding with that producer could try several blocks; this version does not defend against that.
- Reducing a 256-bit number modulo the list's size leaves a bias below 2^-200. It is ignored.

### 1.8 Checking a draw

A verifier **MUST** check each of these, and **MUST** report them as separate failures, because each is a different accusation:

| Check | If it fails |
|---|---|
| `sha256(seed)` equals the committed seed hash | the seed was swapped |
| the list has as many candidates as committed | candidates were added or removed |
| the list's fingerprint equals the committed fingerprint | the list was swapped or reordered |
| the list follows 1.1 | the list is malformed |
| the count drawn equals the committed count | the count was chosen afterwards |
| the recomputed picks equal the claimed picks | the result was forged |

The entropy is checked by the program that records it; a verifier checks that the program is the published one.

---

## 2. What this version does not specify

- **What goes into a round's list.** Which services are open for testing at a time, and how demand puts them there, comes with the parts that bring members and questions on chain.
- **Who opens rounds and how often.** For now anyone may open one, for a bond, and it proves nothing except that its draw was fair.

## Test values

[`vectors/draw.json`](vectors/draw.json) holds inputs, the results every implementation must produce, and lists every implementation must refuse:

```bash
python reference/check.py
cd rust && cargo test
```
