//! Second readings, from SPEC.md section 3.

pub const WORKS_NOW: u8 = 1;
pub const FALSE_OR_DECAYED: u8 = 2;
pub const AGREED_FAILS: u8 = 3;

/// 3.3: what a pair settles, from the first and second verdicts.
pub fn outcome(first: u8, second: u8) -> Option<u8> {
    if !(1..=3).contains(&first) || !(1..=3).contains(&second) {
        return None;
    }
    Some(match (first, second) {
        (_, 1) => WORKS_NOW,
        (1, _) => FALSE_OR_DECAYED,
        _ => AGREED_FAILS,
    })
}

/// A reading of one service, as far as 3.2's ordering needs it.
pub struct Candidate {
    pub id: Vec<u8>,
    pub revealed_slot: u64,
    pub committed_slot: u64,
    pub counts: bool,
}

/// 3.2: the reading a re-read round committed at `round_committed_slot`
/// re-tests: revealed latest, then committed earliest, then smallest id.
pub fn latest(readings: &[Candidate], round_committed_slot: u64) -> Option<&[u8]> {
    readings
        .iter()
        .filter(|r| r.counts && r.revealed_slot < round_committed_slot)
        .min_by(|a, b| {
            b.revealed_slot
                .cmp(&a.revealed_slot)
                .then(a.committed_slot.cmp(&b.committed_slot))
                .then(a.id.cmp(&b.id))
        })
        .map(|r| r.id.as_slice())
}

/// 3.2: whether a second reading counts as one.
pub fn counts(first_reader: &str, second_reader: &str, first_revealed_slot: u64, round_committed_slot: u64,
              same_service: bool, same_round: bool, first_is_latest: bool) -> bool {
    same_service && !same_round && first_is_latest && first_reader != second_reader && first_revealed_slot < round_committed_slot
}
