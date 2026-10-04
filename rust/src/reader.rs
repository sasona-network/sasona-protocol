//! Drawing the member who reads a service, from SPEC.md 4.3.

use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};

pub const MAX_ATTEMPTS: u32 = 16;

/// The seat drawn at `attempt`, numbered from 1, out of the round's `members`
/// (M, at least 1).
pub fn s(final_seed: &[u8; 32], service: &str, attempt: u32, members: u32) -> u32 {
    let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(final_seed).expect("any key length");
    mac.update(b"reader");
    mac.update(&Sha256::digest(service.as_bytes()));
    mac.update(&attempt.to_be_bytes());
    let digest = mac.finalize().into_bytes();
    let m = members as u64;
    let mut acc: u64 = 0;
    for byte in digest {
        acc = (acc * 256 + byte as u64) % m;
    }
    1 + acc as u32
}

/// The seat whose membership reads `service`, or None. `seats` is the roster
/// when the reading is committed: the key in each seat, from seat 1.
pub fn reader(final_seed: &[u8; 32], service: &str, members: u32, seats: &[&str], first_reader: Option<&str>) -> Option<u32> {
    if members == 0 {
        return None;
    }
    (0..MAX_ATTEMPTS)
        .map(|a| s(final_seed, service, a, members))
        .find(|&k| k as usize <= seats.len() && Some(seats[k as usize - 1]) != first_reader)
}
