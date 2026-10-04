//! Every value in vectors/reader.json, reproduced by this implementation.

use sasona_draw::reader::*;

#[test]
fn every_reader() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/reader.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(v["max_attempts"].as_u64().unwrap(), MAX_ATTEMPTS as u64);
    let cases = v["cases"].as_array().unwrap();
    assert!(cases.len() >= 12);
    for c in cases {
        let name = c["name"].as_str().unwrap();
        let seed: [u8; 32] = hex::decode(c["final_seed"].as_str().unwrap()).unwrap().try_into().unwrap();
        let service = c["service"].as_str().unwrap();
        let members = c["members"].as_u64().unwrap() as u32;
        let seats: Vec<Seat> = c["seats"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| Seat { key: x["key"].as_str().unwrap(), since: x["since"].as_u64().unwrap() })
            .collect();
        let draws: Vec<u64> = if members == 0 { vec![] } else { (0..MAX_ATTEMPTS).map(|a| s(&seed, service, a, members) as u64).collect() };
        let want: Vec<u64> = c["attempts"].as_array().unwrap().iter().map(|x| x.as_u64().unwrap()).collect();
        assert_eq!(draws, want, "{name}: the draws");
        let got = reader(&seed, service, members, c["committed_slot"].as_u64().unwrap(), &seats, c["first_reader"].as_str());
        assert_eq!(got.map(|k| k as u64), c["reader"].as_u64(), "{name}");
    }
}
