//! Drawing the member who reads a service, from SPEC.md 4.3.

use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};

pub const MAX_ATTEMPTS: u32 = 16;

/// A membership on a round's roster, as the draw needs it.
pub struct Membership {
    pub key: String,
    pub active: bool,
}

/// The membership drawn at `attempt`, numbered from 1. `members` is at least 1.
pub fn n(final_seed: &[u8; 32], service: &str, attempt: u32, members: u32) -> u32 {
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

/// The membership that reads `service`, or None if no attempt qualifies.
/// `first_reader` is the key that took the first reading, for a second reading.
pub fn reader(final_seed: &[u8; 32], service: &str, memberships: &[Membership], first_reader: Option<&str>) -> Option<u32> {
    let members = memberships.len() as u32;
    if members == 0 {
        return None;
    }
    (0..MAX_ATTEMPTS).map(|a| n(final_seed, service, a, members)).find(|&k| {
        let m = &memberships[k as usize - 1];
        m.active && Some(m.key.as_str()) != first_reader
    })
}
