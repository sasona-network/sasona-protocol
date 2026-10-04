//! Purchases and chargebacks, from SPEC.md section 7.

use sha2::{Digest, Sha256};

use crate::reader::{s, MAX_ATTEMPTS};

pub const REPLAY_DOMAIN: &[u8] = b"sasona/replay/v1";
pub const FEE_BPS: u64 = 500;

/// 7.2: the price times the rate in basis points, over 10,000, rounded down.
pub fn premium(price: u64, rate: u64) -> u64 {
    (price as u128 * rate as u128 / 10_000) as u64
}

/// 7.4: the replayer's pay, and the deposit: 5% of the price, rounded down.
pub fn fee(price: u64) -> u64 {
    (price as u128 * FEE_BPS as u128 / 10_000) as u64
}

/// 7.2: what an open purchase could cost its member.
pub fn counted(price: u64) -> u64 {
    price + fee(price)
}

/// 7.2: the room to insure, in dollar units. The stake's value rounds down,
/// what is owed rounds up. Negative when a member owes more than they hold.
pub fn room(stake: u64, usd_reserve: u64, coin_reserve: u64, open: u64, owed: u64) -> i128 {
    let stake_usd = stake as i128 * usd_reserve as i128 / coin_reserve as i128;
    let owed_usd = (owed as i128 * usd_reserve as i128 + coin_reserve as i128 - 1) / coin_reserve as i128;
    stake_usd - open as i128 - owed_usd
}

/// 7.4: the seed a replay's seat is drawn with.
pub fn replay_seed(chargeback: &[u8; 32], draw: u32, entropy: &[u8; 32]) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(REPLAY_DOMAIN);
    h.update(chargeback);
    h.update(draw.to_be_bytes());
    h.update(entropy);
    h.finalize().into()
}

/// A seat as a replay's draw sees it: who holds it, since when, and the
/// membership in it.
pub struct ReplaySeat<'a> {
    pub key: &'a str,
    pub since: u64,
    pub member: u32,
}

/// 7.4: the seat drawn to replay, passing over seats held by `passed_over`
/// keys, seats whose membership is in `declined`, and seats sat in since
/// `committed_slot`.
pub fn replay_seat(
    seed: &[u8; 32],
    service: &str,
    members: u32,
    committed_slot: u64,
    seats: &[ReplaySeat],
    passed_over: &[&str],
    declined: &[u32],
) -> Option<u32> {
    if members == 0 {
        return None;
    }
    (0..MAX_ATTEMPTS).map(|a| s(seed, service, a, members)).find(|&k| {
        seats.get(k as usize - 1).is_some_and(|seat| {
            seat.since < committed_slot && !passed_over.contains(&seat.key) && !declined.contains(&seat.member)
        })
    })
}

/// 7.5: (to the buyer from the cover, deposit back, deposit to the
/// replayer, fee from the cover, owed by the quoter), in dollar units.
/// `verdict` is None when the replay never happened.
pub fn settle(price: u64, deposit: u64, verdict: Option<u8>) -> (u64, u64, u64, u64, u64) {
    let f = fee(price);
    match verdict {
        Some(1) if deposit > 0 => (0, 0, deposit, 0, 0),
        Some(1) => (0, 0, 0, f, f),
        Some(_) => (price, deposit, 0, f, price + f),
        None => (price, deposit, 0, 0, price),
    }
}
