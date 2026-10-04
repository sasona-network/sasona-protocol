//! The committed question, from SPEC.md section 2.
//!
//! The canonical form is written by hand from the nonce, following 2.3,
//! rather than through a JSON library's own idea of order and escaping.

use sha2::{Digest, Sha256};

pub const DELIVERED: u8 = 1;
pub const WRONG_ANSWER: u8 = 2;
pub const EMPTY: u8 = 3;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

pub fn valid_nonce(nonce: &str) -> bool {
    nonce.len() == 32 && nonce.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

pub fn expected(nonce: &str) -> String {
    hex(&Sha256::digest(nonce.as_bytes()))[..16].to_string()
}

pub fn code_for(nonce: &str) -> String {
    format!("import hashlib\nprint(hashlib.sha256(\"{nonce}\".encode()).hexdigest()[:16])")
}

/// 2.3: a JSON string, escaping only what a question can contain.
fn json_string(s: &str) -> String {
    let mut out = String::from("\"");
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// The canonical JSON of the question for this nonce, keys in byte order:
/// body, capability, code, command, expect, nonce, tier.
pub fn canonical_question(nonce: &str) -> Option<String> {
    if !valid_nonce(nonce) {
        return None;
    }
    let code = json_string(&code_for(nonce));
    Some(format!(
        "{{\"body\":{{\"code\":{code},\"language\":\"python\"}},\"capability\":\"execute\",\"code\":{code},\
         \"command\":[\"python\",\"-c\",{code}],\"expect\":{},\"nonce\":{},\"tier\":1}}",
        json_string(&expected(nonce)),
        json_string(nonce),
    ))
}

pub fn question_hash(nonce: &str) -> Option<[u8; 32]> {
    canonical_question(nonce).map(|j| Sha256::digest(j.as_bytes()).into())
}

pub fn reply_hash(reply: &[u8]) -> [u8; 32] {
    Sha256::digest(reply).into()
}

/// 2.4, for the reading's nonce. None if the nonce is not valid.
pub fn verdict(reply: &[u8], nonce: &str) -> Option<u8> {
    if !valid_nonce(nonce) {
        return None;
    }
    if reply.is_empty() {
        return Some(EMPTY);
    }
    let e = expected(nonce);
    let e = e.as_bytes();
    Some(if reply.windows(e.len()).any(|w| w == e) { DELIVERED } else { WRONG_ANSWER })
}

/// Whether some bytes are exactly the canonical question for the nonce
/// they name.
pub fn is_fair(shown: &[u8]) -> bool {
    let Ok(v) = serde_json::from_slice::<serde_json::Value>(shown) else { return false };
    let Some(nonce) = v.get("nonce").and_then(|n| n.as_str()) else { return false };
    canonical_question(nonce).is_some_and(|c| c.as_bytes() == shown)
}
