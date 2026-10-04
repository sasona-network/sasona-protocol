//! Every value in vectors/chargeback.json, reproduced by this implementation.

use sasona_draw::chargeback::*;
use sasona_draw::reader::{s, MAX_ATTEMPTS};

fn u(v: &serde_json::Value) -> u64 {
    v.as_u64().unwrap()
}

#[test]
fn every_chargeback_value() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/chargeback.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    for c in v["amounts"].as_array().unwrap() {
        let price = u(&c["price"]);
        assert_eq!((premium(price, u(&c["rate"])), fee(price), counted(price)), (u(&c["premium"]), u(&c["fee"]), u(&c["counted"])));
    }
    for c in v["rooms"].as_array().unwrap() {
        let got = room(u(&c["stake"]), u(&c["usd_reserve"]), u(&c["coin_reserve"]), u(&c["open"]), u(&c["owed"]));
        assert_eq!(got, c["room"].as_i64().unwrap() as i128, "{}", c["name"]);
    }
    for c in v["settlements"].as_array().unwrap() {
        let verdict = c["verdict"].as_u64().map(|x| x as u8);
        let want = (u(&c["to_buyer"]), u(&c["deposit_back"]), u(&c["deposit_to_replayer"]), u(&c["fee_from_cover"]), u(&c["owed"]));
        assert_eq!(settle(u(&c["price"]), u(&c["deposit"]), verdict), want, "{}", c["name"]);
    }
    let r = &v["replay"];
    let ident: [u8; 32] = hex::decode(r["chargeback"].as_str().unwrap()).unwrap().try_into().unwrap();
    let entropy: [u8; 32] = hex::decode(r["entropy"].as_str().unwrap()).unwrap().try_into().unwrap();
    let seeds: Vec<String> = (0..2).map(|d| hex::encode(replay_seed(&ident, d, &entropy))).collect();
    let want: Vec<String> = r["seeds"].as_array().unwrap().iter().map(|x| x.as_str().unwrap().to_string()).collect();
    assert_eq!(seeds, want);
    let seed: [u8; 32] = hex::decode(&want[0]).unwrap().try_into().unwrap();
    let service = r["service"].as_str().unwrap();
    let members = u(&r["members"]) as u32;
    let draws: Vec<u64> = (0..MAX_ATTEMPTS).map(|a| s(&seed, service, a, members) as u64).collect();
    let want: Vec<u64> = r["draws"].as_array().unwrap().iter().map(u).collect();
    assert_eq!(draws, want);
    for c in r["seats"].as_array().unwrap() {
        let seats: Vec<ReplaySeat> = c["seats"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| ReplaySeat { key: x["key"].as_str().unwrap(), since: u(&x["since"]), member: u(&x["member"]) as u32 })
            .collect();
        let keys: Vec<&str> = c["passed_over_keys"].as_array().unwrap().iter().map(|x| x.as_str().unwrap()).collect();
        let declined: Vec<u32> = c["declined"].as_array().unwrap().iter().map(|x| u(x) as u32).collect();
        let got = replay_seat(&seed, service, members, u(&r["committed_slot"]), &seats, &keys, &declined);
        assert_eq!(got.map(u64::from), c["seat"].as_u64(), "{}", c["name"]);
    }
}
