//! Sasona protocol: the draw (SPEC.md section 1) here, the committed
//! question (section 2) in `question`, second readings (section 3) in `pair`,
//! and drawing the reader (section 4) in `reader`.
//!
//! Written from the specification rather than translated from the Python
//! reference. Both are ours; an implementation by somebody else is what
//! would really test the specification.

pub mod pair;
pub mod question;
pub mod reader;

use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};

pub const DOMAIN: &[u8] = b"sasona/draw/v1";
pub const ATTEMPTS_PER_CANDIDATE: usize = 64;
pub const MAX_CANDIDATES: usize = 65_536;

#[derive(Debug, PartialEq, Eq)]
pub enum Refused {
    NotAscii,
    NotHttp,
    NoHost,
    Repeated,
    BadCount,
    BadSize,
}

/// SPEC.md 1.1: the host of a candidate, or why the candidate is refused.
pub fn host_of(candidate: &str) -> Result<String, Refused> {
    if candidate.is_empty() || !candidate.bytes().all(|b| (0x21..=0x7E).contains(&b)) {
        return Err(Refused::NotAscii);
    }
    let (scheme, rest) = candidate.split_once("://").ok_or(Refused::NotHttp)?;
    let scheme = scheme.to_ascii_lowercase();
    let default_port = match scheme.as_str() {
        "https" => ":443",
        "http" => ":80",
        _ => return Err(Refused::NotHttp),
    };
    let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    let mut authority = &rest[..end];
    if let Some(at) = authority.rfind('@') {
        authority = &authority[at + 1..];
    }
    let mut host = authority.to_ascii_lowercase();
    if host.ends_with(default_port) {
        host.truncate(host.len() - default_port.len());
    }
    if host.ends_with('.') {
        host.pop();
    }
    if host.is_empty() {
        return Err(Refused::NoHost);
    }
    Ok(host)
}

/// sha256 over each candidate followed by a zero byte, in order.
pub fn pool_fingerprint(candidates: &[String]) -> [u8; 32] {
    let mut h = Sha256::new();
    for c in candidates {
        h.update(c.as_bytes());
        h.update([0u8]);
    }
    h.finalize().into()
}

pub fn seed_hash(seed: &[u8; 32]) -> [u8; 32] {
    Sha256::digest(seed).into()
}

pub fn final_seed(seed: &[u8; 32], entropy: &[u8; 32]) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(DOMAIN);
    h.update(seed);
    h.update(entropy);
    h.finalize().into()
}

/// HMAC-SHA256(final seed, label || attempt as 4 big-endian bytes), read as
/// one big-endian number, reduced modulo `n`. Reduced byte by byte, so no
/// 256-bit integer type is needed: (acc * 256 + byte) mod n at each step.
fn pick(final_seed: &[u8; 32], label: &[u8], attempt: u32, n: usize) -> usize {
    let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(final_seed).expect("any key length");
    mac.update(label);
    mac.update(&attempt.to_be_bytes());
    let digest = mac.finalize().into_bytes();
    let n = n as u128;
    let mut acc: u128 = 0;
    for byte in digest {
        acc = (acc * 256 + byte as u128) % n;
    }
    acc as usize
}

pub fn draw(candidates: &[String], final_seed: &[u8; 32], count: usize) -> Result<Vec<String>, Refused> {
    if candidates.is_empty() || candidates.len() > MAX_CANDIDATES {
        return Err(Refused::BadSize);
    }
    let mut seen = std::collections::HashSet::new();
    if !candidates.iter().all(|c| seen.insert(c)) {
        return Err(Refused::Repeated);
    }
    if count == 0 || count > candidates.len() {
        return Err(Refused::BadCount);
    }

    let mut hosts: Vec<String> = Vec::new();
    let mut endpoints: Vec<Vec<&String>> = Vec::new();
    for c in candidates {
        let h = host_of(c)?;
        match hosts.iter().position(|x| *x == h) {
            Some(i) => endpoints[i].push(c),
            None => {
                hosts.push(h);
                endpoints.push(vec![c]);
            }
        }
    }

    let mut picked: Vec<String> = Vec::new();
    let cap = ATTEMPTS_PER_CANDIDATE * candidates.len();
    let mut attempt = 0usize;
    while picked.len() < count && attempt < cap {
        let host = pick(final_seed, b"host", attempt as u32, hosts.len());
        let options = &endpoints[host];
        let candidate = options[pick(final_seed, b"endpoint", attempt as u32, options.len())];
        if !picked.contains(candidate) {
            picked.push(candidate.clone());
        }
        attempt += 1;
    }
    Ok(picked)
}
