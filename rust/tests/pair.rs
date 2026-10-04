//! Every value in vectors/pair.json, reproduced by this implementation.

use sasona_draw::pair::*;

#[test]
fn every_pair() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/pair.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let outcomes = v["outcomes"].as_array().unwrap();
    assert_eq!(outcomes.len(), 9);
    for o in outcomes {
        let got = outcome(o["first"].as_u64().unwrap() as u8, o["second"].as_u64().unwrap() as u8).unwrap();
        assert_eq!(got as u64, o["outcome"].as_u64().unwrap(), "{}", o["outcome_name"]);
    }
    for c in v["counting"].as_array().unwrap() {
        let got = counts(
            c["first_reader"].as_str().unwrap(),
            c["second_reader"].as_str().unwrap(),
            c["first_revealed_slot"].as_u64().unwrap(),
            c["round_committed_slot"].as_u64().unwrap(),
            c["same_service"].as_bool().unwrap(),
            c["same_round"].as_bool().unwrap(),
            c["first_is_latest"].as_bool().unwrap(),
        );
        assert_eq!(got, c["counts"].as_bool().unwrap(), "{}", c["name"]);
    }
    for c in v["latest"].as_array().unwrap() {
        let readings: Vec<Candidate> = c["readings"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| Candidate {
                id: hex::decode(r["id"].as_str().unwrap()).unwrap(),
                revealed_slot: r["revealed_slot"].as_u64().unwrap(),
                committed_slot: r["committed_slot"].as_u64().unwrap(),
                counts: r["counts"].as_bool().unwrap(),
            })
            .collect();
        let want = c["latest"].as_str().map(|s| hex::decode(s).unwrap());
        let got = latest(&readings, c["round_committed_slot"].as_u64().unwrap()).map(|b| b.to_vec());
        assert_eq!(got, want, "{}", c["name"]);
    }
    assert_eq!(outcome(0, 1), None);
    assert_eq!(outcome(1, 4), None);
}
