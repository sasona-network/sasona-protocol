//! Quotes and the ranking, from SPEC.md section 6.

pub const TERM_SECONDS: i64 = 30 * 24 * 60 * 60;

/// A quote on one reading, with what 6.2 needs to know about it at a moment.
pub struct Quote {
    pub reading: Vec<u8>,
    /// Basis points; 0 if withdrawn.
    pub rate: u32,
    /// The reading passes 2.7 and was not upheld false.
    pub counts: bool,
    pub verdict: u8,
    /// Set by the key that took the reading.
    pub by_reader: bool,
    /// The reading was taken by a member.
    pub by_member: bool,
    pub revealed_time: i64,
    /// Its membership is active at the moment asked about.
    pub member_active: bool,
}

/// 6.1 and 6.2: whether the quote stands at `at`.
pub fn stands(q: &Quote, at: i64) -> bool {
    (1..=10_000).contains(&q.rate)
        && q.counts
        && q.verdict == 1
        && q.by_reader
        && q.by_member
        && q.member_active
        && at <= q.revealed_time + TERM_SECONDS
}

/// 6.3: the services with a premium, cheapest first, as (service, premium).
pub fn rank<'a>(services: &'a [(String, Vec<Quote>)], at: i64) -> Vec<(&'a str, u32)> {
    // The order of quotes: lowest rate, then revealed latest, then smaller reading.
    let key = |q: &Quote| (q.rate, std::cmp::Reverse(q.revealed_time), q.reading.clone());
    let mut priced: Vec<_> = services
        .iter()
        .filter_map(|(service, quotes)| {
            quotes.iter().filter(|q| stands(q, at)).min_by_key(|q| key(q)).map(|q| (key(q), service.as_str()))
        })
        .collect();
    priced.sort();
    priced.into_iter().map(|((rate, _, _), service)| (service, rate)).collect()
}
