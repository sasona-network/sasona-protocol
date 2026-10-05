# Sasona protocol

**Version 0.8.0.** This version specifies the draw (section 1), the committed question (section 2), second readings (section 3), members (section 4), challenges (section 5), the ranking (section 6), chargebacks (section 7) and payment channels (section 8).

0.8.0 adds section 8, and the markup on every purchase (8.1), which a covered purchase now pays too (7.2). 0.7.0 added section 7, and a reading now records where its service asks to be paid (2.5). 0.6.0 added section 6. 0.5.0 added sections 4 and 5, and limits a reply to its first 10,000 bytes (2.4); no reading so far had a reply that long. 0.4.0 added section 3. 0.3.0 added section 2. 0.2.0 added that a list can be drawn once (1.3, 1.8) and stated two limits more plainly (1.7). Every value 0.1.0 computes is unchanged.

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

**A list is drawn once.** The round's address on chain is derived from the pool fingerprint alone, so only one round can ever exist for a given list in a given order, whoever opens it. Otherwise an opener could open several rounds for the same list with different seeds, reveal them all, and keep whichever result they liked. A verifier **MUST** take the round at the address derived from the list's fingerprint, and no other.

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
- Whoever produces the entropy slot does not know the seed, unless they are the opener or work with the opener. Solana publishes which validator produces each slot an epoch ahead, so a validator can open a round timed for the target slot to land in their own run of slots. They can then try different contents for that block, or skip it so the entropy moves to a later slot they also produce. This version does not defend against an opener who is, or is working with, the validator producing the target slot.
- Reordering the same services gives a new fingerprint and so a new round. An opener who dislikes a result can withhold it, losing the bond, and open the list again in another order. The bond is what that costs.
- Reducing a 256-bit number modulo the list's size leaves a bias below 2^-200. It is ignored.

### 1.8 Checking a draw

A verifier **MUST** check each of these, and **MUST** report them as separate failures, because each is a different accusation:

| Check | If it fails |
|---|---|
| `sha256(seed)` equals the committed seed hash | the seed was swapped |
| the list has as many candidates as committed | candidates were added or removed |
| the list's fingerprint equals the committed fingerprint | the list was swapped or reordered |
| the round is the one at the address derived from that fingerprint | the round was one of several, and the others were hidden |
| the list follows 1.1 | the list is malformed |
| the count drawn equals the committed count | the count was chosen afterwards |
| the recomputed picks equal the claimed picks | the result was forged |

The entropy is checked by the program that records it; a verifier checks that the program is the published one.

---

## 2. The committed question

A member tests a drawn service by asking it something whose right answer only the member knows. The question is fixed on chain **before** the service is called, and revealed afterwards, so it cannot be reshaped to fit whatever came back. The verdict comes from a published rule that anyone holding the reply can run again.

### 2.1 The challenge

This version specifies one capability, `execute`: a service that runs code and returns what it printed. It is a closed loop: the member holds the answer before asking.

- The **nonce** is 16 fresh random bytes, written as 32 lowercase hex characters. A nonce **MUST NOT** be used twice, and the program refuses one that has been revealed before.
- The **expected answer** is the first 16 characters of the lowercase hex `sha256` of the nonce's 32 ASCII characters.
- The **code** is exactly these two lines, joined by one newline `0x0A` and with no newline at the end, `<nonce>` replaced by the nonce:

```
import hashlib
print(hashlib.sha256("<nonce>".encode()).hexdigest()[:16])
```

The expected answer is a hash of the nonce rather than the nonce itself, so a service that echoes the request back does not contain it.

### 2.2 The question

The question is a JSON object with exactly these seven keys:

| Key | Value |
|---|---|
| `capability` | `"execute"` |
| `nonce` | the nonce |
| `expect` | the expected answer |
| `tier` | `1` |
| `code` | the code |
| `command` | `["python", "-c", <code>]` |
| `body` | `{"code": <code>, "language": "python"}` |

The code is carried in all three shapes a service may accept, so the commitment covers whichever one is sent.

**Only the code goes to the service**, in one of the shapes `code`, `command` or `body`. The question object itself **MUST NOT** be sent: it holds the expected answer, and a service that echoed it back would pass.

### 2.3 The question's bytes and hash

The question is hashed as exactly one sequence of bytes, its **canonical form**:

- keys sorted by their bytes, ascending, at both levels: `body`, `capability`, `code`, `command`, `expect`, `nonce`, `tier`, and inside `body`, `code` then `language`
- no whitespace: separators are exactly `,` and `:`
- strings in double quotes. In the code, `"` is written as backslash and quote, and the newline as backslash and `n`. Nothing else in a question needs escaping, because every other character is printable ASCII
- the tier written as the single digit `1`

```
question_hash = sha256( canonical form )
```

This is not a general JSON encoding. It is the one byte sequence 2.1 and 2.2 produce for a nonce, and an implementation can build it directly from the nonce. Any other bytes, even ones a JSON parser reads as the same object, are a different question.

### 2.4 The reply and the verdict

The reply is the bytes the service returned, exactly as received, up to the first 10,000. Bytes after those are not part of the reply. Its **reply hash** is `sha256` of the reply.

The limit is what a member can put on chain in answer to a challenge (section 5). A reply cut at 10,000 bytes is judged on what it keeps, so an answer that only appears later is not found. The challenge's program prints 16 characters, so a service that delivers does not need more.

| Verdict | Code | When |
|---|---|---|
| `delivered` | 1 | the expected answer for the reading's nonce, as 16 ASCII bytes, appears anywhere in the reply |
| `wrong_answer` | 2 | the reply is not empty and does not contain them |
| `empty` | 3 | the reply is empty |

The rule works on bytes, not text: the reply need not be valid UTF-8, and the answer must appear in lowercase, unbroken.

A service that returned no reply at all, because it could not be reached or refused payment, took no money and gave nothing to read. That is not a reading and is not recorded.

### 2.5 What a reading records, and in what order

1. The member commits the question hash on chain for one service of a drawn round.
2. The member sends that service the code, and keeps the reply.
3. The member reveals the nonce, the reply hash and the verdict, and the address the service asks to be paid at, if it names one (7.1).

The reply hash **MUST** be of the first 10,000 bytes of what came back (2.4), never more. The program cannot see the reply, and a hash of a longer one is a reading its member can never back if challenged.

At the reveal, the program builds the canonical question from the nonce itself and **MUST** refuse the reveal unless its hash is the committed one, so only a fair question can ever be revealed.

**A nonce belongs to the reading that committed to it earliest.** The service learns the nonce when it is called, which is after the honest reading was committed. It can copy the nonce into a reading of its own, and reveal that first, but it can never commit earlier. So when a reading reveals a nonce that another reading already holds, the program **MUST** hand the nonce to it if it was committed in a strictly earlier slot, and **MUST** refuse it otherwise. Without this, a failing service could make every reading of itself impossible to reveal, and the reader would look like the one who backed out.

A reading not revealed within 9,000 slots, about an hour, can only be marked **lapsed**, and is recorded as such.

### 2.6 What a reading does and does not prove

- **The question was fixed first.** It was committed before the reveal, so it was not chosen to fit the reply, and it is the fair question for a nonce never used before.
- **The record agrees with itself.** Anyone holding the reply can hash it, compare the hash, and run the verdict rule again. The reply is what the network sells, so only its hash goes on chain.
- **The member's word is still the member's word.** The member alone holds the reply, and the service does not sign it. A dishonest member could write down any reply they liked, containing the answer or not, and everything above would still check out. What makes that costly is not this section: it is second readings (section 3), the stake a member can lose (section 5), and a buyer's chargeback (part 7). A web proof of the reply, which would take the member out of it, is a later version.
- **`delivered` means the answer came back, not how.** A service that recognises this program and computes the hash without running any code also passes. An `execute` reading checks the answer the code produces.
- A reading does not prove when the service was called.
- A member can still choose not to reveal a reading they dislike. It is then marked lapsed, in public.
- A member working with a service could tell it a nonce in advance. Nothing here can see that.

### 2.7 Checking a reading

| Check | If it fails |
|---|---|
| the canonical question for the revealed nonce hashes to the committed hash | the question was changed after the commitment |
| `sha256(reply)` equals the recorded reply hash | the reply shown is not the one that was read |
| the verdict rule on the reply gives the recorded verdict | the verdict was misreported |
| the nonce's record names this reading | the nonce was used by an earlier reading, and this one does not count |
| the reading's service is, byte for byte, one of its round's published picks, or the reading is a replay drawn as 7.4 says | the service was not drawn, or was spelt differently to be tested twice |
| the reader holds the membership drawn for the service (4.3) | the reader chose themselves |
| no challenge to the reading was upheld (5.3) | its member could not back it |

## 3. Second readings

A reading can be wrong, and a service that worked can stop working. A second reading tests the service again, and set beside the first, it settles some of that.

### 3.1 Which readings are re-read

They are drawn, not chosen. A **re-read round** is an ordinary round (section 1) whose list is services that already have a revealed reading. Its picks are read again.

Two numbers come out of this and they **MUST NOT** be reported as one:

- the share of readings **drawn** for a second reading, which is a choice, made when the re-read round is committed
- the share actually **re-read**, which is the measurement

A round can draw every reading and re-read none of them. Reporting the first as if it were the second reports an intention as a result.

### 3.2 A second reading

A second reading is an ordinary reading (section 2) taken in a re-read round, which names, when it is committed, the first reading it re-tests. The first reading is not the second reader's to choose: it is the **latest** reading of that service that counts (2.7) and was revealed before the re-read round was committed. A reader who could name any earlier reading could pick the one whose verdict they want to contradict.

Latest means revealed in the latest slot. Between readings revealed in the same slot, it is the one committed earliest, and then the one whose identifier is smallest, compared as bytes.

It counts only if:

- it is of the same service, byte for byte
- the first reading is the latest one of that service, as above
- the two were taken in different rounds
- the second reader is not the first reader. Someone checking their own reading checks nothing

### 3.3 What a pair settles

| Outcome | Code | When |
|---|---|---|
| `works_now` | 1 | the second reading is `delivered` |
| `false_or_decayed` | 2 | the first is `delivered` and the second is not |
| `agreed_fails` | 3 | neither is `delivered` |

`works_now` does not say whether the first reading was right. A service that failed then and delivers now works now, whichever reading was wrong.

`false_or_decayed` **MUST NOT** be reported as a false reading. A service that delivered in September can fail in November because a quota ran out or a key expired, with nobody lying. Whether the first reading was false is a question about the first reading's own evidence, and a second reading cannot answer it.

### 3.4 What a pair does not prove

- **A different key is not a different person** (4.5). What the second reader has to lose is their stake (section 5).
- **Both readings are still their readers' word**, as 2.6 says of every reading.
- **Which reading is re-read is fixed, but not when.** Whoever opens a re-read round picks the moment, and so which reading is the latest at that moment. Someone can also take a reading of a service just before a re-read round opens, and make theirs the one that gets re-read, but only if they are drawn to read it (4.3).

### 3.5 Checking a pair

| Check | If it fails |
|---|---|
| both readings pass 2.7 | one of them does not count, and neither does the pair |
| the services are the same bytes | it is a reading of something else |
| the first was revealed before the re-read round was committed | which reading is the latest was not settled when the list was committed |
| no other reading of the service that counts comes after the first, as 3.2 orders them, and was revealed before the re-read round was committed | the second reader chose which reading to contradict |
| the readers differ | it is a reading checking itself |
| the recorded outcome follows 3.3 from the two verdicts | the outcome was misreported |

A pair settled before one of its readings was upheld false (5.3) keeps the outcome recorded on chain, and by the first row no longer counts. A pair whose second reading was upheld false before settling never settles.

## 4. Members

A member is someone with a stake locked in the network. Readings are taken by members, and the member who reads a service is drawn, not chosen.

### 4.1 Memberships

A **membership** is one stake of a fixed size, locked in coin. Memberships are numbered from 1 in the order they were taken, and a number is never reused. Readings and challenges name memberships by this number.

One key may hold several. Every draw below is over memberships, so a key with three has three chances, and it locked three stakes to get them. Splitting the same coins over more keys buys nothing.

### 4.2 The roster

The **roster** is the memberships that can be drawn, in seats numbered from 1 to **A**, with no gaps:

- a membership that is taken sits in seat `A + 1`
- a membership that asks to leave, or loses its stake, leaves its seat at once. The membership in the last seat moves into it, and the roster is one shorter

So every seat holds an active membership, and nothing that has left stays on the roster to be drawn and passed over. Each seat also records the slot its membership sat down in, whether by joining or by moving up.

When a round is committed, the program records **M**, the number of seats then. Only a membership already in its seat at that slot can read for the round.

### 4.3 Drawing the reader

For a service `S` of a drawn round:

```
s(a) = 1 + ( int( HMAC-SHA256( key = final_seed,
                               message = "reader" || sha256(S) || u32_be(a) ),
                  big-endian over all 32 bytes ) mod M )
```

for attempts `a = 0, 1, 2, ...`. When the reading is committed, the reader is the membership in seat `s(a)` for the first attempt where:

- seat `s(a)` exists now, that is `s(a) <= A`. The roster can be shorter than it was when the round was committed
- the membership in it sat down before the round was committed. One that joined since, or moved up into the seat since, is passed over. Otherwise someone could leave, rejoin into the last seat and read whatever was drawn to it
- for a second reading, the membership in it is not held by the key that took the first reading

At most 16 attempts are made. If none qualifies, nobody reads `S` in this round.

- the key is the round's **final seed** (1.5), the same seed its picks were drawn with
- the label is the ASCII bytes `reader`, then the 32 bytes of `sha256(S)`, then the attempt as 4 bytes, big-endian
- a round with `M = 0` has no readers

The program **MUST** refuse a reading committed by anyone other than the key holding the membership drawn for it. Whoever commits shows the seats passed over that exist, so the program can check each one.

A reading **MUST** be committed within 9,000 slots, about an hour, of the slot the round's entropy came from (1.4). A service its drawn member has not committed to by then goes unread in this round, in public: its reading is missing.

Readings taken before version 0.5.0 have no membership. Their round's opener took them.

### 4.4 Leaving

A membership asks to leave, and leaves its seat at once. Its stake comes back after 45 days' notice. A reading can be challenged for 30 days after it is revealed, and a challenge answered for 7 more (section 5), so the notice outlasts every challenge a member's readings can get. A membership with an open challenge, a covered purchase still open, or anything owed to the cover (section 7) cannot take its stake back until that is settled.

### 4.5 What membership does and does not prove

- **A membership is a stake, not a person.** Two memberships can be one person, and nothing here can tell.
- **The stake is the same for everyone.** A stake that deters has to grow with what a false reading would be worth, which is the traffic a service carries. That needs purchases on chain (parts 7 and 8).
- **Who reads is drawn, but a drawn member can decline,** by not committing, or by leaving. The service then goes to its next attempt or unread in that round, and the record shows which. The member who moves up into a freed seat does not read for rounds committed before the move, neither for the seat it left nor for the one it took.
- **A departure moves two seats' draws on.** When a membership leaves its seat, what was drawn to that seat and what was drawn to the last seat both go to their next attempt, for every round still in its hour. Whoever leaves picks the moment after the draw is public, and so does whoever upholds a challenge against a seated member, who need not be a member at all. Each departure costs a membership, so a group can only move draws on in proportion to the memberships it gives up.
- **The reader picks the moment within the hour.** A reader working with a service can wait inside the window for it to be up.
- **The opener writes the list and chooses when to open it.** As 1.7 says of the picks, an opener can also withhold a round after seeing the draw, which now includes its readers.

## 5. Challenges

### 5.1 What a challenge asks

Anyone may challenge a reading taken by a member, once, within 30 days of its reveal, for a bond of 0.1 SOL. The challenge asks the member to show what they recorded:

- the nonce
- the reply, in full, at most 10,000 bytes (2.4)

They have 7 days to put both on chain.

### 5.2 The answer

The answer holds if:

- the nonce's record names this reading (2.5)
- `sha256(reply)` is the reply hash the reading recorded
- the verdict rule (2.4) on the reply, for this nonce, gives the verdict the reading recorded

If it holds, the challenger's bond goes to the member, who paid to publish. The reply stays on chain and can no longer be changed.

### 5.3 A challenge upheld

If no answer holds by the deadline, anyone may uphold the challenge. Then:

- the reading no longer counts
- the membership loses its whole stake, and its seat if it still has one
- the challenger gets the bond back, and a tenth of the stake
- the rest of the stake goes into the cover (part 1), first to pay back what the member owes it (7.5)

What the member owes the cover comes out first, and the challenger's tenth is a tenth of what is left. If nobody holds any of the cover, the coin is burned instead. It was never in the pool, so the price does not move.

If the stake has already come back to the member, the reading still stops counting.

> **Temporary.** The stake, the bond and the challenger's tenth are devnet figures: at these numbers a challenge can cost more than it wins. They are set together, from what readings are worth, once purchases are on chain (parts 7 and 8).

### 5.4 What a challenge does and does not prove

- **It catches a member who cannot back their own record.** A verdict that does not follow from the reply, a reply hash that was never a reply, a reply that was not kept.
- **It does not catch a reply made up well.** A member knows the nonce, so they can write a reply that passes, and it will. 2.6 still holds. What catches that is a buyer's chargeback, which replays the purchase (part 7), and later a web proof of the reply.
- **A service that stopped working is not a false reading.** Nothing in this section looks at the service again. A `false_or_decayed` pair (3.3) is never, by itself, grounds to take a stake.
- **A reading can be challenged once.** A challenge that is answered settles the record for good, including when the challenger was the member's friend. All it settles is that the record agrees with itself.

### 5.5 Checking a challenge

| Check | If it fails |
|---|---|
| the reading was revealed, by a member, no more than 30 days before the challenge | there is nothing to challenge |
| the answer's nonce record names the reading | the nonce is someone else's |
| `sha256(reply)` equals the recorded reply hash | the reply shown is not the one recorded |
| the verdict rule on the reply gives the recorded verdict | the verdict was misreported |
| an upheld challenge had no answer that held within its 7 days | the stake was taken from a member who had answered |

## 6. Quotes and the ranking

The member who read a service is the one who knows most about it right now. They say what they would charge to insure a purchase from it. Services are ranked by that price: cheap to insure ranks first, expensive ranks last, and a service nobody will insure is not listed. Nobody else decides the order.

### 6.1 A quote

A **quote** is a rate in basis points, from 1 to 10,000, of a purchase's price: what a buyer would pay to be covered if the purchase does not deliver. It is set on one reading, by the key that took it. The member can change the rate or withdraw it at any time.

The program refuses a rate unless the reading was revealed, says `delivered`, was taken by a member who is still active, and is no more than 30 days old. It cannot see the rest of 2.7, whether the service was one of its round's picks and whether the reading still holds its nonce, so whoever ranks checks those (6.5).

Each change is recorded on chain, with its slot and time, in the event the program emits. The quote's account holds only the latest rate.

### 6.2 Which readings count for a service

At the moment the ranking is read, a service's readings are those that count (2.7) and were revealed by then, ordered as in 3.2: revealed in the latest slot first, then committed earliest, then the smaller identifier.

A **failing pair** is two readings next to each other in that order that both say the service did not deliver, taken by different keys. One failing reading is not enough. A reader can make a failing reply up as easily as anything else, and it costs them nothing (5.4), so one reader alone cannot take a service off the list. Two, from two keys, say it more firmly, whether the service failed from the start or stopped working since (3.3).

A quote on one of the readings **stands** if:

- its reading is newer than the latest failing pair, if there is one
- its reading says `delivered` and is no more than 30 days old at that moment
- its rate is from 1 to 10,000, set by the reading's member, whose membership is still active

So once two keys have found a service failing, every quote given before stops counting, and it takes a newer reading, quoted by its own member, to list the service again. Taking a service off the list needs two keys; putting it back needs one reading and someone willing to insure it.

### 6.3 The ranking

At the moment it is read:

1. a service is **listed** if at least one quote on its readings stands
2. its **premium** is the lowest rate among those quotes. If several share it, the one that counts is on the latest reading, as 6.2 orders them
3. listed services are ranked from the lowest premium to the highest
4. services with the same premium are ranked by the reading behind their premium, the latest first
5. services that are not listed are not ranked

So the lowest price any member still stands behind is the price. A member who stops quoting, leaves, or reads the service as failed does not take it off the list while another member's quote stands. The member whose quote is the premium is the one who carries the risk when purchases are covered (parts 7 and 8), so a quote that is too low costs whoever gave it, and a member who has changed their mind raises it or withdraws it.

The ranking is of the moment it is read. The chain keeps each quote's latest rate, and a membership's and a reading's present state, so a ranking for a moment in the past is rebuilt from the program's events, not from accounts.

### 6.4 What a quote does and does not prove

- **Until purchases are on chain, a quote costs nothing to give.** The ranking is what members say they would charge, not yet what they have to pay. Premiums are collected with purchases (part 8), and claims paid from stakes with chargebacks (part 7). That is what makes a low quote expensive to give falsely. A member can also withdraw a quote and set it again when it suits them, and nothing here sees it.
- **Being the reader is not expensive.** Anyone can open a round with a list of their choosing, and an operator holding several memberships can open rounds that list only their own service until one of their memberships is drawn, then quote it cheaply. Nothing here stops that price from being the premium. Once purchases are covered at it (parts 7 and 8), it is what they pay out at. The same works the other way, more weakly: to take a rival off the list takes two failing readings from two keys, which one person holding two memberships can still arrange. Which services go into lists is not specified yet (section 7), and until it is, a ranking is only as good as the readings behind it.
- **One reading puts a service back on the list** after two keys found it failing, if its member quotes it, and an operator holding memberships can arrange that reading as above. Its quote is new, though, and its member is the one exposed by it.
- **A failing service can stay listed** after one honest reading finds it failing, at a quote set before, until a second reading from another key agrees or its quote runs out. The member who set that quote is the one exposed while it stands.
- **The stake does not grow with the quote.** Every membership has the same stake, whatever it insures. 4.5 says when that changes.

### 6.5 Checking a ranking

Whoever ranks needs, besides the program's accounts: each round's published list, to check the service was one of its picks, and each reading's reveal, to find its nonce and check the nonce record.

| Check | If it fails |
|---|---|
| the readings weighed are those that count, revealed by the moment of the ranking | a reading that does not count moved the price |
| each premium is the lowest quote that stands, as 6.2 says | a higher price was shown, or a stale one used |
| no quote counted is on a reading older than the service's latest failing pair | a price set before two keys found the service failing was used |
| the quote was set by the key that took the reading | someone else priced a reading they did not take |
| the order follows 6.3 | the services were reordered |

## 7. Purchases and chargebacks

A buyer whose purchase did not deliver is paid back. Nobody decides it by opinion: a member drawn for it tests the service again, and the rule of section 2 says whether it delivered. The cover pays the buyer at once, and the member who insured the purchase pays the cover back, out of their stake.

### 7.1 Where a service is paid

When a member reads a service, they also record the address the service asks to be paid at. A purchase covered on that reading can be paid to that address only. Without this, a buyer could name themselves as the merchant, buy nothing, and claim the price back.

### 7.2 A covered purchase

A **covered purchase** is recorded on chain when it is made. It names the reading whose quote covers it, and the program refuses it unless that quote stands as far as the program can see (6.1), and unless the price is at least a minimum the network sets. The buyer pays, through the program:

- the **price**, to the address recorded on the covering reading, where it settles for good. The merchant is never asked for it back
- the **premium**, the price times the quote's rate in basis points, divided by 10,000 and rounded down, to the member who set the quote
- the **markup** on the price (8.1), to the network

The buyer names the highest rate they accept, and the purchase is refused if the quote was raised past it before the purchase landed.

A member insures only up to their stake. Their **room to insure** is their stake, valued in dollars at the pool's price, less what their open purchases could cost them, less what they owe the cover (7.5). An open purchase could cost its price and the replayer's 5%, and a purchase that would take that past the room is refused. A purchase is open until its 7 days to charge back have passed, or its chargeback is settled. A member with purchases open, or owing the cover, cannot take their stake back (4.4).

Nothing in the program lowers the pool's price (part 1): no instruction sells coin into the pool, and a claim burns coin in proportion to the dollars it takes. So a stake's value in dollars can only rise after it is counted. This is a rule the program **MUST** keep: an instruction that lowered the price would let members insure more than their stakes are worth. Anyone can raise the price, and every stake's room with it, by adding dollars to the pool (part 1), but that money stays in the pool for good.

### 7.3 A chargeback

Within 7 days of the purchase, its buyer may ask for the price back, once, with a **deposit** of 5% of the price. A chargeback needs no deposit if no chargeback, with a deposit or without, was made on that service in the 30 days before it: the first buyer to find a service failing should not pay to say so. A service is its endpoint's exact bytes, so two spellings of one address count as two services.

### 7.4 The replay

A chargeback is settled by a **replay**: a reading of the service, like any other (section 2), taken by a member drawn for that chargeback alone.

- **The draw.** A draw records the slot it is made in and the number of seats then. Its seed is `sha256("sasona/replay/v1" || chargeback || u32_be(draw number) || entropy)`, where `chargeback` is the chargeback's 32-byte identifier, draws are numbered from 0, and the entropy is taken as in 1.4 from the first slot 32 after the draw's. The seat is then drawn as in 4.3, with this seed in place of the round's final seed and the draw's number of seats as M. No member holds a seed back to see it first. Anyone may record the entropy, and the member drawn records it when they commit their reading. The reader is drawn as in 4.3, passing over every seat held by the buyer's key or by the key that set the quote, and every seat held by a membership that already declined this chargeback.
- **A decline.** A draw **counts** once its hour to read (4.3) has passed with no reading committed, or with one committed and never revealed (2.5). The membership drawn then counts as declined, or, for a reading committed and never revealed, the membership that committed it, whatever seat either holds later. A draw whose entropy was never recorded, and can no longer be, also counts once the same hour, from the entropy's slot, has passed, but its seat cannot be known, and nobody is passed over for it. Then anyone may draw again. So whoever dislikes the seat a draw will give can let it pass, but only by using up one of the draws.
- **The end.** After 8 draws that count, or 7 days after the chargeback, whichever comes first, the chargeback is settled as if the replay had not delivered. A replay already committed is waited for until its hour to reveal is over. Finding out is the network's burden, not the buyer's.
- **The pay.** The member who replays is paid 5% of the price, rounded down, whatever their verdict. The deposit is the same amount.

### 7.5 What the replay settles

| The replay | The buyer | The replayer's 5% | The member who set the quote |
|---|---|---|---|
| delivers | is not paid back; the deposit is the replayer's 5% | from the deposit, or, for a first chargeback, from the cover | owes the cover the replayer's 5% for a first chargeback |
| does not deliver, or never happens | is paid back the price by the cover, and the deposit from where it was held | from the cover | owes the cover all of it |

The cover pays as a claim does (part 1): dollars leave the pool, and equal coin is burned from the pool and from the cover, so the price does not move. What the member owes the cover is that coin. It is taken from their stake into the cover once the covering reading can no longer be challenged (5.1), so a stake cannot be turned into dollars early by a member charging back their own purchase while a challenge to their reading could still come. A membership left with less than a whole stake (4.1) leaves its seat and starts its notice to leave (4.4).

The markup a covered purchase paid (8.1) is not paid back, whatever the replay finds.

When a reading is shown false (section 5), its member's taken stake goes into the cover, first to pay back what they owe it (5.3).

The cover pays only what it can (part 1): a claim may not empty it, nor take more dollars than the pool holds. A chargeback the cover cannot pay yet waits, and is paid when it can.

### 7.6 Replays among the other readings

A replay is a reading, and counts as one (2.7) if its draw follows 7.4: it stands in place of being one of a round's picks. It is weighed in the ranking (section 6) like any other, so a replay that fails is one key towards a failing pair. Its reader may quote on it.

### 7.7 What a chargeback does and does not prove

- **The insurer pays for decay, which departs from the paper.** The paper puts a service that worked and stopped on the cover, with nobody at fault. Here the member who insured it pays the cover back. A replay cannot tell a reading that was false from a service that decayed, and if the cover paid for decay, a member could quote a service, collect the premiums, and leave every loss to the depositors. Whether the reading was false stays a separate question, for section 5.
- **The replay tests the service now, with the network's own question, not the buyer's request.** A buyer's request can be any code, and there is no rule anyone can run to say whether a reply to it was delivery. So a chargeback pays back any covered purchase of a service that fails now, whether or not that purchase failed, and pays nothing for one that failed and works again. One replay decides, so a service that fails some of the time can go either way.
- **A replay that never happens pays the buyer,** whether the members drawn were working with someone or only offline, and the insurer pays for it.
- **A replayer can make up their verdict.** Working with the member who set the quote, they can make up a reply that passes, and the buyer loses the deposit. Working with the buyer, they can make up one that fails, and the member pays for a service that works. Section 5 cannot catch a reply made up well (5.4). The draw, and passing over the buyer's and the quoter's seats, is all that stands in the way; a buyer can let up to 7 draws pass to look for a friend (7.4).
- **Someone has to draw again.** Draws do not repeat on their own. A member whose quote is charged back has every reason to keep drawing until a replay happens, and if nobody does within 7 days, they pay.
- **A first chargeback costs the member who set the quote.** It needs no deposit, so the replayer's 5% is the member's. A rival can buy once every 30 days at the minimum price and charge it back, paying the price's markup each time. The minimum price is what bounds that.
- **The payout address is its reader's word,** and the reader is usually the one who quotes. A member who records their own address and buys from themselves only moves dollars to themselves that their own stake pays back.
- **Who is passed over.** The draw passes over the buyer's and the quoting member's seats, and those that declined. Other members who quote the same service, or who have chargebacks open against it, are not passed over, and nor is the service's operator: the program cannot see everyone who holds a position.
- **The draw's entropy** is a slot's hash, with the limits 1.7 states.
- **A quote can stop standing in ways the program cannot see** (6.1). A purchase made under it is still covered, and its member still pays.
- **A challenge upheld while a chargeback is open** takes the stake before it can pay the cover back. Nine tenths of it go to the cover anyway, and the challenger's tenth is out of reach.
- **Not covered yet.** The paper's further rules are not part of this version: a service failing some of the time marked as such, and a service with too many chargebacks needing a larger stake, then removed.

### 7.8 Checking a chargeback

| Check | If it fails |
|---|---|
| the purchase was paid to the address its covering reading recorded, under a quote that stood (6.2) | the buyer was paid back on a purchase nobody insured |
| the purchase paid its markup (8.1) | the network was bypassed |
| each draw follows 7.4 from its slot, and passes over the seats 7.4 names | the replay was chosen |
| what was paid, and by whom, follows 7.5 from the replay's verdict or its absence | the outcome was misreported |
| what the member owed was taken from their stake once their reading could no longer be challenged | an insurer was let off |

## 8. Payment channels

An agent buying a service many times a minute cannot put each payment on chain: a transaction costs more than most calls. A **channel** holds the agent's dollars in the program, and the agent pays by signing, off chain, how much the service may take from it so far. The service takes it on chain when it likes, once for many calls. The money is in nobody's hands but the program's, and the service can never take more than the agent signed.

### 8.1 The markup on every purchase

Every purchase carries a **markup**, paid by the buyer on top of the price: for a price `p`, `markup(p) = ceil(15 × p / 100)`, the 15 points of the fee table. This holds for a covered purchase (7.2) and for a payment through a channel. The markup is held in the network's fee account and turned into coin later, by anyone, as the fee table sets: 5 of its 15 points stay in the pool as depth, and the rest is shared among the participants.

Participants' shares go to the network until purchases can be told apart from a participant paying itself, and the program MUST keep it so. A markup proves only that someone paid it, not that a purchase happened: a buyer can buy from their own address, and a payer can pay an address of their own through a channel. Paying a participant from such a markup would let them buy coin at a discount.

A covered purchase pays the markup on its price, beside the premium. It is not counted in the room to insure. A chargeback does not return it: the buyer is paid back the price (7.5), and the markup has already paid for the reading and the cover the buyer bought with it.

### 8.2 A channel

A channel is opened by a **payer**, who MUST sign the opening, for one **payee** address. Its address is derived from `"channel"`, the payer, the payee and an identifier as 8 bytes little-endian. The program keeps for each payer one record, never closed, holding the next identifier. It starts at 0, only opening a channel creates it or moves it, and each opening takes its identifier and adds one. So no channel address is ever used twice. The payer pays that record's rent once, and does not get it back.

The payee MUST NOT be the pool, the network's vault, or the owner of the fee account or of the cover's vault: money sent there would be counted by nobody. Any other address of the program's is a donation that does no harm. A channel named as payee, for one, gets dollars in its account that go back to its own payer at close.

A channel records:

- the **signer**: the key whose vouchers the channel honours. It is fixed when the channel is opened, and is the payer's own key unless the payer names another. The signer MUST sign the opening, and MUST NOT be the payee.
- what has been put in. Only the payer adds to it, and only while no close is pending.
- what the payee has taken so far, and the markup charged on it
- the markup owed on what was taken, not yet moved to the network
- the slot a close was asked for, if one was

Each channel holds its dollars in its own token account, owned by the channel's address, so that channels never wait on each other or on the pool. The payer pays the rent of both and gets it back when the channel closes. After every instruction that moves a channel's dollars, the program MUST check that its token account holds at least what was put in, less what was taken and the markup moved out of it. Not exactly: anyone can send dollars to the account, and an exact check would let one stray unit stop the channel. Anything more than the record goes back to the payer at close. The program MUST also check that what was taken plus the markup charged is at most what was put in.

Apart from that, the payee is any address. A payer paying a service it found through a reading names the address that reading recorded (7.1), so that the channel pays the service the ranking stands behind.

### 8.3 A voucher

A **voucher** is the signer's ed25519 signature over 90 bytes:

| Bytes | |
|---|---|
| 17 | `"sasona/voucher/v1"` |
| 32 | the program's address |
| 1 | the cluster: 1 for devnet. Mainnet will have its own number. |
| 32 | the channel's address |
| 8 | the amount, big-endian |

The amount is **cumulative**: everything the payee may have taken from the channel, in dollar units, since it was opened. A payer paying for one more call signs a voucher larger than the last by that call's price. A larger voucher replaces every smaller one, and a payee needs to keep only the largest.

The channel's address is never reused (8.2), so a voucher is worth something for one channel only. The cluster number is compiled into the program, with the dollar it accepts. A build for another cluster MUST carry another number, and the build MUST refuse to compile until both are set for it, so that a voucher signed on devnet is worth nothing on mainnet even if the program keeps its address.

### 8.4 Taking payment

Anyone may show the program a voucher for a channel, while it is open or within the notice (8.5). With `D` what has been put in and `v` the voucher's amount, the program:

1. checks the signature as 8.6 requires
2. works out what the channel can pay: `x = min(v, floor(100 × D / 115))`, computed without overflow. This is the largest amount whose price and markup fit in `D`.
3. refuses unless `x` is more than what the payee has taken
4. pays the difference to the payee's dollar account: an account of the token program whose mint is the dollar and whose owner is the payee
5. charges `markup(x)` less the markup already charged, and records it on the channel as owed to the network

The markup stays in the channel's own account until anyone sweeps it, or the channel closes. Then it moves to the network's fee account and is counted with the markup held there. A sweep with nothing owed is refused. A payment touches only the channel, its account and the payee's.

So a voucher the channel cannot fully cover still pays what it can. Taking a voucher at once or in many pieces costs the same markup. Whatever is left when the channel closes is `D` less what was taken and `markup` of it. A payee whose dollar account is frozen or closed cannot be paid until it fixes it; that costs only the payee.

### 8.5 Closing

- **The payee may close** at any time. The markup owed moves to the network, and whatever is left goes back to the payer, with the rent.
- **The payer may ask to close,** once. A second ask is refused, and an ask cannot be withdrawn. The notice ends at the slot it was asked in plus **648,000**, about 72 hours. Before that slot the payee may still take payment, and nobody may finish closing. From that slot on, nobody may take payment, and anyone may finish closing: the markup owed moves to the network, and whatever is left goes back to the payer, with the rent.

The notice is counted in slots, so a cluster that stops does not use it up. A payee must take its largest voucher within the notice, or lose it. A payee that takes payment at least once a day is never at risk of more than a day's vouchers.

### 8.6 Checking the signature

Solana checks ed25519 signatures in a separate instruction of the same transaction, which the program reads back. The program MUST refuse unless:

- the instruction just before the one taking payment is an instruction of the ed25519 program `Ed25519SigVerify111111111111111111111111111`
- it checks exactly one signature
- its three instruction-index fields are all `u16::MAX`, so that the key, the signature and the message are read from that instruction itself
- the key, read at the key offset that instruction's header gives, is the channel's signer, byte for byte
- the message, read at the message offset and length that header gives, is 90 bytes long and exactly those of 8.3 for this channel and the amount shown

The program reads the key and the message through the header's offsets, the same ones the ed25519 program used, never at fixed positions. Each of these checks has been the hole in some deployed program. A program that finds the signature anywhere else in the transaction, or compares bytes other than the ones that were verified, can be made to accept a signature the signer never made.

### 8.7 What a payee checks before serving

A voucher is only worth what the channel can pay. Before serving, a payee checks on chain, or from what it has already seen:

- the channel exists, names it as payee, and has no close pending
- `floor(100 × D / 115)` covers the new voucher
- the signer is the key it expects

### 8.8 What a channel does and does not do

- **It takes the float off us.** The paper names holding agents' money as one of the places the network is centralised. A channel holds it in the program, and a payment is a signature, not a balance on our books.
- **Payments in a channel are not covered.** A covered purchase (section 7) is recorded on chain one by one, at a minimum price, and can be charged back. A channel payment is not recorded and cannot be. A payer wanting cover buys through section 7.
- **The payee is trusted to deliver,** call by call. The payer risks one call's price at a time, and stops signing when it is cheated.
- **The markup is taken on what is paid out, not on what is signed.** Two parties can always settle outside the network. What the markup buys inside it is money held by the program rather than by either party, and a payee the ranking stands behind.
- **The signer is the hook for part 9.** A payer can let a key with less power sign, and keep its own key offline. The payer must make that key itself: a key handed over by the service would let the service sign its own vouchers. A signer key that leaks can pay only the payee, up to what the channel holds. Part 9's ceiling is what bounds it further.
- **A payee can close a channel as soon as it is funded.** It costs the payer a transaction, and nothing else.

### 8.9 Checking a channel

| Check | If it fails |
|---|---|
| everything paid out of a channel is backed by a voucher its signer signed, at most its amount in total | the payee took what it was not given |
| the markup paid out of a channel is `markup` of everything taken | the network was bypassed, or the payer overcharged |
| what goes back to the payer is what was put in, less what was taken and its markup | the payer was short-changed |
| each channel's account holds at least what was put in, less what was taken and the markup moved out | the channel's money went somewhere it should not |

## 9. What this version does not specify

- **What goes into a round's list.** Which services are open for testing at a time, and how demand puts them there, comes with the parts that bring members and questions on chain.
- **Who opens rounds and how often.** For now anyone may open one, for a bond, and it proves nothing except that its draw was fair.
- **Capabilities other than `execute`.**

## Test values

[`vectors/draw.json`](vectors/draw.json), [`vectors/question.json`](vectors/question.json), [`vectors/pair.json`](vectors/pair.json), [`vectors/reader.json`](vectors/reader.json) [`vectors/ranking.json`](vectors/ranking.json), [`vectors/chargeback.json`](vectors/chargeback.json) and [`vectors/channel.json`](vectors/channel.json) hold inputs, the results every implementation must produce, and what every implementation must refuse:

```bash
python reference/check.py
cd rust && cargo test
```
