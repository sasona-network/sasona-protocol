//! Every value in vectors/ranking.json, reproduced by this implementation.

use sasona_draw::ranking::*;

fn quote(v: &serde_json::Value) -> Quote {
    Quote {
        reading: hex::decode(v["reading"].as_str().unwrap()).unwrap(),
        rate: v["rate"].as_u64().unwrap() as u32,
        counts: v["counts"].as_bool().unwrap(),
        verdict: v["verdict"].as_u64().unwrap() as u8,
        by_reader: v["by_reader"].as_bool().unwrap(),
        by_member: v["by_member"].as_bool().unwrap(),
        revealed_time: v["revealed_time"].as_i64().unwrap(),
        member_active: v["member_active"].as_bool().unwrap(),
    }
}

#[test]
fn every_ranking() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../vectors/ranking.json");
    let v: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(v["term_seconds"].as_i64().unwrap(), TERM_SECONDS);
    let standing = v["standing"].as_array().unwrap();
    assert!(standing.len() >= 10);
    for c in standing {
        assert_eq!(stands(&quote(&c["quote"]), c["at"].as_i64().unwrap()), c["stands"].as_bool().unwrap(), "{}", c["name"]);
    }
    let rankings = v["rankings"].as_array().unwrap();
    assert!(rankings.len() >= 6);
    for c in rankings {
        let services: Vec<(String, Vec<Quote>)> = c["services"]
            .as_object()
            .unwrap()
            .iter()
            .map(|(s, qs)| (s.clone(), qs.as_array().unwrap().iter().map(quote).collect()))
            .collect();
        let got = rank(&services, c["at"].as_i64().unwrap());
        let want: Vec<(String, u64)> = c["ranking"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| (x[0].as_str().unwrap().to_string(), x[1].as_u64().unwrap()))
            .collect();
        let got: Vec<(String, u64)> = got.into_iter().map(|(s, r)| (s.to_string(), r as u64)).collect();
        assert_eq!(got, want, "{}", c["name"]);
    }
}
