//! Every value in vectors/draw.json, reproduced by this implementation.

use sasona_draw::*;

fn vectors() -> serde_json::Value {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/draw.json");
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
}

fn bytes32(v: &serde_json::Value) -> [u8; 32] {
    hex::decode(v.as_str().unwrap()).unwrap().try_into().unwrap()
}

fn strings(v: &serde_json::Value) -> Vec<String> {
    v.as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_string()).collect()
}

fn base58(s: &str) -> Vec<u8> {
    const ALPHABET: &[u8] = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    let mut out: Vec<u8> = Vec::new(); // little-endian base-256 digits
    for ch in s.bytes() {
        let mut carry = ALPHABET.iter().position(|&a| a == ch).unwrap() as u32;
        for d in out.iter_mut() {
            carry += *d as u32 * 58;
            *d = (carry & 0xff) as u8;
            carry >>= 8;
        }
        while carry > 0 {
            out.push((carry & 0xff) as u8);
            carry >>= 8;
        }
    }
    let zeros = s.bytes().take_while(|&b| b == b'1').count();
    let mut bytes = vec![0u8; zeros];
    bytes.extend(out.iter().rev());
    bytes
}

#[test]
fn hosts() {
    for (url, host) in vectors()["hosts"].as_object().unwrap() {
        assert_eq!(host_of(url).unwrap(), host.as_str().unwrap(), "{url}");
    }
}

#[test]
fn every_case() {
    let v = vectors();
    let cases = v["cases"].as_array().unwrap();
    assert!(cases.len() >= 8);
    for c in cases {
        let name = c["name"].as_str().unwrap();
        let candidates = strings(&c["candidates"]);
        let seed = bytes32(&c["seed"]);
        let entropy = bytes32(&c["entropy"]);
        assert_eq!(base58(c["entropy_base58"].as_str().unwrap()), entropy.to_vec(), "{name}: entropy byte order");
        assert_eq!(hex::encode(seed_hash(&seed)), c["seed_hash"].as_str().unwrap(), "{name}: seed hash");
        assert_eq!(hex::encode(pool_fingerprint(&candidates)), c["pool_fingerprint"].as_str().unwrap(), "{name}: fingerprint");
        let fin = final_seed(&seed, &entropy);
        assert_eq!(hex::encode(fin), c["final_seed"].as_str().unwrap(), "{name}: final seed");
        let count = c["count"].as_u64().unwrap() as usize;
        assert_eq!(draw(&candidates, &fin, count).unwrap(), strings(&c["picks"]), "{name}: picks");
    }
}

#[test]
fn every_refusal() {
    let v = vectors();
    let refused = v["refused"].as_array().unwrap();
    assert!(refused.len() >= 10);
    for r in refused {
        let candidates = strings(&r["candidates"]);
        let count = r["count"].as_u64().unwrap() as usize;
        assert!(draw(&candidates, &[0u8; 32], count).is_err(), "accepted: {}", r["why"]);
    }
}
