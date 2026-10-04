//! Quotes and the ranking, from SPEC.md section 6.

use std::cmp::Reverse;

pub const TERM_SECONDS: i64 = 30 * 24 * 60 * 60;

/// One reading of a service, with its quote.
pub struct Reading {
    pub id: Vec<u8>,
    /// Who took it.
    pub key: String,
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

/// 6.2: the readings that count and were revealed by `now`, latest first.
pub fn weighed(readings: &[Reading], now: i64) -> Vec<&Reading> {
    let mut w: Vec<&Reading> = readings.iter().filter(|r| r.counts && r.revealed_time <= now).collect();
    w.sort_by_key(|r| order(r));
    w
}

/// 6.2: the weighed readings newer than the latest failing pair: two readings
/// next to each other that both failed, taken by different keys.
pub fn newer_than_failing_pair(readings: &[Reading], now: i64) -> Vec<&Reading> {
    let mut w = weighed(readings, now);
    if let Some(i) = w.windows(2).position(|p| p[0].verdict != 1 && p[1].verdict != 1 && p[0].key != p[1].key) {
        w.truncate(i);
    }
    w
}

/// 6.2: whether the quote on a weighed reading stands at `now`.
pub fn stands(r: &Reading, now: i64) -> bool {
    r.verdict == 1
        && now <= r.revealed_time + TERM_SECONDS
        && (1..=10_000).contains(&r.quote)
        && r.quote_by_reader
        && r.member_active
}

/// 6.3, steps 1 and 2: the reading whose quote is the premium, if listed.
pub fn behind(readings: &[Reading], now: i64) -> Option<&Reading> {
    newer_than_failing_pair(readings, now).into_iter().filter(|r| stands(r, now)).min_by_key(|r| (r.quote, order(r)))
}

pub fn premium(readings: &[Reading], now: i64) -> Option<u32> {
    behind(readings, now).map(|r| r.quote)
}

/// 6.3: the listed services, cheapest first, as (service, premium).
pub fn rank<'a>(services: &'a [(String, Vec<Reading>)], now: i64) -> Vec<(&'a str, u32)> {
    let mut listed: Vec<_> = services
        .iter()
        .filter_map(|(service, readings)| behind(readings, now).map(|r| (r.quote, order(r), service.as_str())))
        .collect();
    listed.sort();
    listed.into_iter().map(|(p, _, service)| (service, p)).collect()
}
