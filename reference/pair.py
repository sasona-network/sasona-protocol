"""Second readings, as SPEC.md section 3 defines them. Standard library only."""

DELIVERED = 1
WORKS_NOW, FALSE_OR_DECAYED, AGREED_FAILS = 1, 2, 3
OUTCOMES = {WORKS_NOW: "works_now", FALSE_OR_DECAYED: "false_or_decayed", AGREED_FAILS: "agreed_fails"}


def outcome(first: int, second: int) -> int:
    """SPEC.md 3.3, from the two verdicts (1 delivered, 2 wrong_answer, 3 empty)."""
    if first not in (1, 2, 3) or second not in (1, 2, 3):
        raise ValueError("a verdict is 1, 2 or 3")
    if second == DELIVERED:
        return WORKS_NOW
    if first == DELIVERED:
        return FALSE_OR_DECAYED
    return AGREED_FAILS


def latest(readings: list, round_committed_slot: int):
    """SPEC.md 3.2: the reading a re-read round re-tests, or None.

    Each reading is a dict with "id" (hex), "revealed_slot", "committed_slot"
    and "counts" (whether it passes 2.7)."""
    eligible = [r for r in readings if r["counts"] and r["revealed_slot"] < round_committed_slot]
    if not eligible:
        return None
    return min(eligible, key=lambda r: (-r["revealed_slot"], r["committed_slot"], bytes.fromhex(r["id"])))["id"]


def counts(first_reader: str, second_reader: str, first_revealed_slot: int, round_committed_slot: int,
           same_service: bool, same_round: bool, first_is_latest: bool) -> bool:
    """SPEC.md 3.2: whether a second reading counts as one."""
    return (same_service and not same_round and first_is_latest and first_reader != second_reader
            and first_revealed_slot < round_committed_slot)
