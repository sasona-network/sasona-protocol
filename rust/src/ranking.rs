//! Quotes and the ranking, from SPEC.md section 6.

use std::cmp::Reverse;

pub const TERM_SECONDS: i64 = 30 * 24 * 60 * 60;

/// One reading of a service, with its quote.
pub struct Reading {
    pub id: Vec<u8>,
    pub revealed_slot: u64,
    pub committed_slot: u64,
    pub revealed_time: i64,
    /// Passes 2.7 and was not upheld false.
    pub counts: bool,
    pub verdict: u8,
    /// Its membership is active now.
    pub member_active: bool,
    /// Basis points; 0 if there is none or it was withdrawn.
    pub quote: u32,
    pub quote_by_reader: bool,
}

/// 3.2's order: the smallest key is the latest reading.
fn order(r: &Reading) -> (Reverse<u64>, u64, Vec<u8>) {
    (Reverse(r.revealed_slot), r.committed_slot, r.id.clone())
}

/// 6.2: the latest reading that counts.
pub fn current(readings: &[Reading]) -> Option<&Reading> {
    readings.iter().filter(|r| r.counts).min_by_key(|r| order(r))
}

/// 6.3, steps 1 and 2: the premium now, or None if the service is not listed.
pub fn premium(readings: &[Reading], now: i64) -> Option<u32> {
    let r = current(readings)?;
    let listed = r.verdict == 1
        && r.revealed_time <= now
        && now <= r.revealed_time + TERM_SECONDS
        && (1..=10_000).contains(&r.quote)
        && r.quote_by_reader
        && r.member_active;
    listed.then_some(r.quote)
}

/// 6.3: the listed services, cheapest first, as (service, premium).
pub fn rank<'a>(services: &'a [(String, Vec<Reading>)], now: i64) -> Vec<(&'a str, u32)> {
    let mut listed: Vec<_> = services
        .iter()
        .filter_map(|(service, readings)| {
            premium(readings, now).map(|p| (p, order(current(readings).expect("listed")), service.as_str()))
        })
        .collect();
    listed.sort();
    listed.into_iter().map(|(p, _, service)| (service, p)).collect()
}
