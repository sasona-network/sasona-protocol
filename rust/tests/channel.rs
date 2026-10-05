//! Every value in vectors/channel.json, reproduced by this implementation,
//! and the voucher's signature checked with an ed25519 library.

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use sasona_draw::channel::*;

fn u(v: &serde_json::Value) -> u64 {
    v.as_u64().unwrap()
}

fn h32(v: &serde_json::Value) -> [u8; 32] {
    hex::decode(v.as_str().unwrap()).unwrap().try_into().unwrap()
}

fn b58(s: &str) -> [u8; 32] {
    const A: &str = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    let mut out = [0u8; 32];
    for c in s.chars() {
        let mut carry = A.find(c).unwrap() as u32;
        for b in out.iter_mut().rev() {
            carry += *b as u32 * 58;
            *b = carry as u8;
            carry >>= 8;
        }
    }
    out
}

fn result(r: Result<(u64, u64), Refused>) -> serde_json::Value {
    match r {
        Ok((a, b)) => serde_json::json!([a, b]),
        Err(_) => serde_json::json!("refused"),
    }
}

#[test]
fn every_channel_value() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/channel.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    for c in v["markups"].as_array().unwrap() {
        assert_eq!(markup(u(&c["price"])), u(&c["markup"]));
    }
    for c in v["payables"].as_array().unwrap() {
        assert_eq!(payable(u(&c["voucher"]), u(&c["put_in"])), u(&c["payable"]), "{}", c["name"]);
    }

    let w = &v["voucher"];
    let program = b58(w["program"].as_str().unwrap());
    let channel = h32(&w["channel"]);
    let message = voucher_message(&program, u(&w["cluster"]) as u8, &channel, u(&w["amount"]));
    assert_eq!(hex::encode(message), w["message"].as_str().unwrap());
    let public = VerifyingKey::from_bytes(&h32(&w["signer"])).unwrap();
    let published = Signature::from_slice(&hex::decode(w["signature"].as_str().unwrap()).unwrap()).unwrap();
    assert!(public.verify(&message, &published).is_ok());
    let other = voucher_message(&program, 2, &channel, u(&w["amount"]));
    assert_eq!(hex::encode(other), w["message_for_cluster_2"].as_str().unwrap());
    assert!(public.verify(&other, &published).is_err());

    let mut ch: Option<Channel> = None;
    for s in v["life"].as_array().unwrap() {
        let op = s["op"].as_array().unwrap();
        let got = match op[0].as_str().unwrap() {
            "open" => {
                ch = Some(Channel::open(u(&op[1])));
                serde_json::Value::Null
            }
            "pay" => result(ch.as_mut().unwrap().pay(u(&op[1]), u(&op[2]))),
            "sweep" => match ch.as_mut().unwrap().sweep() {
                Ok(m) => serde_json::json!(m),
                Err(_) => serde_json::json!("refused"),
            },
            "donate" => {
                ch.as_mut().unwrap().donate(u(&op[1]));
                serde_json::Value::Null
            }
            "close" => result(ch.as_mut().unwrap().close(u(&op[1]), op[2].as_bool().unwrap())),
            other => panic!("{other}"),
        };
        assert_eq!(got, s["result"], "{}", s["name"]);
    }

    let n = &v["notice"];
    assert_eq!(u(&n["notice_slots"]), NOTICE_SLOTS);
    for c in n["cases"].as_array().unwrap() {
        let mut k = Channel::open(u(&n["put_in"]));
        k.ask_to_close(u(&n["asked"])).unwrap();
        let slot = u(&c["slot"]);
        let ok = match c["op"].as_str().unwrap() {
            "pay" => k.pay(u(&n["voucher"]), slot).is_ok(),
            "finish" => k.close(slot, false).is_ok(),
            "add" => k.add(1).is_ok(),
            "ask" => k.ask_to_close(slot).is_ok(),
            other => panic!("{other}"),
        };
        assert_eq!(ok, c["allowed"].as_bool().unwrap(), "{}", c["name"]);
    }
}
