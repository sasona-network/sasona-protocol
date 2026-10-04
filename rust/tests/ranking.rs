//! Every value in vectors/ranking.json, reproduced by this implementation.

use sasona_draw::ranking::*;

fn reading(v: &serde_json::Value) -> Reading {
    Reading {
        id: hex::decode(v["id"].as_str().unwrap()).unwrap(),
        revealed_slot: v["revealed_slot"].as_u64().unwrap(),
        committed_slot: v["committed_slot"].as_u64().unwrap(),
        revealed_time: v["revealed_time"].as_i64().unwrap(),
        counts: v["counts"].as_bool().unwrap(),
        verdict: v["verdict"].as_u64().unwrap() as u8,
        member_active: v["member_active"].as_bool().unwrap(),
        quote: v["quote"].as_u64().unwrap() as u32,
        quote_by_reader: v["quote_by_reader"].as_bool().unwrap(),
    }
}

fn readings(v: &serde_json::Value) -> Vec<Reading> {
    v.as_array().unwrap().iter().map(reading).collect()
}

#[test]
fn every_ranking() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/ranking.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(v["term_seconds"].as_i64().unwrap(), TERM_SECONDS);
    let premiums = v["premiums"].as_array().unwrap();
    assert!(premiums.len() >= 18);
    for c in premiums {
        let got = premium(&readings(&c["readings"]), c["now"].as_i64().unwrap());
        assert_eq!(got.map(u64::from), c["premium"].as_u64(), "{}", c["name"]);
    }
    let rankings = v["rankings"].as_array().unwrap();
    assert!(rankings.len() >= 5);
    for c in rankings {
        let services: Vec<(String, Vec<Reading>)> =
            c["services"].as_object().unwrap().iter().map(|(s, rs)| (s.clone(), readings(rs))).collect();
        let got: Vec<(String, u64)> =
            rank(&services, c["now"].as_i64().unwrap()).into_iter().map(|(s, p)| (s.to_string(), p as u64)).collect();
        let want: Vec<(String, u64)> = c["ranking"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| (x[0].as_str().unwrap().to_string(), x[1].as_u64().unwrap()))
            .collect();
        assert_eq!(got, want, "{}", c["name"]);
    }
}
