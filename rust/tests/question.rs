//! Every value in vectors/question.json, reproduced by this implementation.

use sasona_draw::question::*;

fn vectors() -> serde_json::Value {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/question.json");
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
}

#[test]
fn questions() {
    let v = vectors();
    let qs = v["questions"].as_array().unwrap();
    assert!(qs.len() >= 3);
    for c in qs {
        let nonce = c["nonce"].as_str().unwrap();
        assert_eq!(expected(nonce), c["expect"].as_str().unwrap());
        assert_eq!(code_for(nonce), c["code"].as_str().unwrap());
        assert_eq!(canonical_question(nonce).unwrap(), c["canonical"].as_str().unwrap());
        assert_eq!(hex::encode(question_hash(nonce).unwrap()), c["question_hash"].as_str().unwrap());
    }
}

#[test]
fn bad_nonces() {
    for b in vectors()["bad_nonces"].as_array().unwrap() {
        assert!(canonical_question(b["nonce"].as_str().unwrap()).is_none(), "{}", b["why"]);
    }
}

#[test]
fn verdicts() {
    let v = vectors();
    let nonce = v["verdicts"]["nonce"].as_str().unwrap();
    let replies = v["verdicts"]["replies"].as_array().unwrap();
    assert!(replies.len() >= 11);
    for r in replies {
        let reply = hex::decode(r["reply_hex"].as_str().unwrap()).unwrap();
        assert_eq!(hex::encode(reply_hash(&reply)), r["reply_hash"].as_str().unwrap());
        assert_eq!(verdict(&reply, nonce).unwrap() as u64, r["verdict"].as_u64().unwrap(), "{}", r["name"]);
    }
}

#[test]
fn fairness() {
    let v = vectors();
    assert!(is_fair(v["fair"].as_str().unwrap().as_bytes()));
    for u in v["unfair"].as_array().unwrap() {
        assert!(!is_fair(u["bytes"].as_str().unwrap().as_bytes()), "{}", u["name"]);
    }
}
