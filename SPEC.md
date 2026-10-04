# Sasona protocol

**Version 0.6.0.** This version specifies the draw (section 1), the committed question (section 2), second readings (section 3), members (section 4), challenges (section 5) and the ranking (section 6).

0.6.0 adds section 6. 0.5.0 added sections 4 and 5, and limits a reply to its first 10,000 bytes (2.4); no reading so far had a reply that long. 0.4.0 added section 3. 0.3.0 added section 2. 0.2.0 added that a list can be drawn once (1.3, 1.8) and stated two limits more plainly (1.7). Every value 0.1.0 computes is unchanged.

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
3. The member reveals the nonce, the reply hash and the verdict.

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
| the reading's service is, byte for byte, one of its round's published picks | the service was not drawn, or was spelt differently to be tested twice |
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

A membership asks to leave, and leaves its seat at once. Its stake comes back after 45 days' notice. A reading can be challenged for 30 days after it is revealed, and a challenge answered for 7 more (section 5), so the notice outlasts every challenge a member's readings can get. A membership with an open challenge cannot take its stake back until the challenge is settled.

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
- the rest of the stake is held to pay back buyers of purchases made on false readings

If the stake has already come back to the member, the reading still stops counting.

> **Temporary.** Until chargebacks are on chain (part 7), the held stake cannot leave. Where it goes is decided there. The stake, the bond and the challenger's tenth are devnet figures: at these numbers a challenge can cost more than it wins. They are set together, from what readings are worth, once purchases are on chain (parts 7 and 8).

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

A **quote** is a rate in basis points, from 1 to 10,000, of a purchase's price: what a buyer would pay to be covered if the purchase does not deliver. It is set on one reading, by the key that took it, and only if:

- the reading counts (2.7) and its verdict is `delivered`. A service that did not deliver is not insured, so it is not listed
- the reading was taken by a member (section 4)

The member can change the rate or withdraw it at any time. The program records each change with its slot and its time. A quote that rises is the member saying the service looks worse than it did.

### 6.2 When a quote stands

At a moment `T`, a quote **stands** if:

- it has a rate, that is, it was not withdrawn
- its reading still counts. One upheld false (5.3) no longer does
- `T` is within 30 days of the reading's reveal, the term a reading is current for
- its membership is active at `T`. A member who has asked to leave, or lost the stake, insures nothing new

### 6.3 The ranking

At a moment `T`, for a list of services:

1. a service's **premium** is the lowest rate among the standing quotes on its readings. If several quotes share it, the one that counts is on the reading revealed latest, then the smaller reading identifier
2. services with a premium are ranked from the lowest premium to the highest
3. services with the same premium are ranked by the reading behind the lowest quote: revealed latest first, then the smaller reading identifier, compared as bytes
4. services with no standing quote are not ranked

The fresher reading wins a tie because it says more about the service now.

### 6.4 What a quote does and does not prove

- **Until purchases are on chain, a quote costs nothing to give.** The ranking is what members say they would charge, not yet what they have to pay. Premiums are collected with purchases (part 8), and claims paid from stakes with chargebacks (part 7). That is what makes a low quote expensive to give falsely.
- **A quote is one member's price, on one reading.** Several readings of the same service each carry their own. The ranking takes the lowest, so one member willing to insure cheaply is enough to rank a service high, and will be the one paying if they were wrong.
- **The stake does not grow with the quote.** Every membership has the same stake, whatever it insures. 4.5 says when that changes.

### 6.5 Checking a ranking

| Check | If it fails |
|---|---|
| each quote ranked is on a reading that counts and says `delivered` | a service that did not deliver was listed |
| it was set by the key that took the reading | someone else priced a reading they did not take |
| it stands at `T`, as 6.2 says | an old, withdrawn or abandoned price was used |
| each service's premium is its lowest standing quote | a higher price was shown than a member offered |
| the order follows 6.3 | the services were reordered |

## 7. What this version does not specify

- **What goes into a round's list.** Which services are open for testing at a time, and how demand puts them there, comes with the parts that bring members and questions on chain.
- **Who opens rounds and how often.** For now anyone may open one, for a bond, and it proves nothing except that its draw was fair.
- **Capabilities other than `execute`.**

## Test values

[`vectors/draw.json`](vectors/draw.json), [`vectors/question.json`](vectors/question.json), [`vectors/pair.json`](vectors/pair.json), [`vectors/reader.json`](vectors/reader.json) and [`vectors/ranking.json`](vectors/ranking.json) hold inputs, the results every implementation must produce, and what every implementation must refuse:

```bash
python reference/check.py
cd rust && cargo test
```
