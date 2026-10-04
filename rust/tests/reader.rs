//! Every value in vectors/reader.json, reproduced by this implementation.

use sasona_draw::reader::*;

#[test]
fn every_reader() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/reader.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(v["max_attempts"].as_u64().unwrap(), MAX_ATTEMPTS as u64);
    let cases = v["cases"].as_array().unwrap();
    assert!(cases.len() >= 9);
    for c in cases {
        let name = c["name"].as_str().unwrap();
        let seed: [u8; 32] = hex::decode(c["final_seed"].as_str().unwrap()).unwrap().try_into().unwrap();
        let service = c["service"].as_str().unwrap();
        let memberships: Vec<Membership> = c["memberships"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| Membership { key: m["key"].as_str().unwrap().to_string(), active: m["active"].as_bool().unwrap() })
            .collect();
        let members = memberships.len() as u32;
        let draws: Vec<u64> = if members == 0 {
            vec![]
        } else {
            (0..MAX_ATTEMPTS).map(|a| n(&seed, service, a, members) as u64).collect()
        };
        let want: Vec<u64> = c["attempts"].as_array().unwrap().iter().map(|x| x.as_u64().unwrap()).collect();
        assert_eq!(draws, want, "{name}: the draws");
        let got = reader(&seed, service, &memberships, c["first_reader"].as_str());
        assert_eq!(got.map(|k| k as u64), c["reader"].as_u64(), "{name}");
    }
}
