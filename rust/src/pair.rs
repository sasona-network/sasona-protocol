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

/// 3.2: whether a second reading counts as one.
pub fn counts(first_reader: &str, second_reader: &str, first_revealed_slot: u64, round_committed_slot: u64,
              same_service: bool, same_round: bool, first_is_latest: bool) -> bool {
    same_service && !same_round && first_is_latest && first_reader != second_reader && first_revealed_slot < round_committed_slot
}
