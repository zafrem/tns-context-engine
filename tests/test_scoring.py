from helpers import ROOT, load_yaml, meta

ACTION_ORDER = ["block", "review", "flag", "pass"]


def cfg():
    return load_yaml(ROOT / "scoring" / "scoring.yml")


def test_rank_weights_are_non_decreasing():
    w = cfg()["rank_weight"]
    assert w == sorted(w) and len(w) == 5


def test_thresholds_strictly_descending_end_at_zero_and_use_known_actions():
    t = cfg()["thresholds"]
    mins = [x["min"] for x in t]
    assert mins == sorted(mins, reverse=True) and len(set(mins)) == len(mins)
    assert mins[-1] == 0
    assert all(x["action"] in meta()["actions"] for x in t)
    idx = [ACTION_ORDER.index(x["action"]) for x in t]
    assert idx == sorted(idx), "actions must get milder as score decreases"


def test_category_overrides_are_known_and_keep_review_band():
    review_min = min(x["min"] for x in cfg()["thresholds"] if x["action"] == "review")
    for cat, o in cfg()["category_overrides"].items():
        assert cat in meta()["categories"], cat
        if "block_min" in o:
            assert o["block_min"] > review_min, f"{cat}: block_min would erase the review band"


def test_floor_router_and_fuse_are_consistent():
    c = cfg()
    assert 1 <= c["floor"]["rank"] <= 5 and 0 <= c["floor"]["min_score"] <= 100
    r = c["router"]
    assert r["clean_below"] < r["definite_min"]
    assert r["nlp_confident_lo"] < r["nlp_confident_hi"]
    assert abs(sum(c["fuse"]["weights"].values()) - 1.0) < 1e-9


def test_router_defines_what_an_ambiguous_hit_is():
    assert 0 < cfg()["router"]["ambiguous_min"] <= 1


def test_floor_matches_the_review_band_and_definite_matches_router():
    c = cfg()
    review_min = min(x["min"] for x in c["thresholds"] if x["action"] == "review")
    definite_min = min(x["min"] for x in c["thresholds"] if x["label"] == "definite")
    assert c["floor"]["min_score"] >= review_min, "a floored rank-5 match must land in review or stricter"
    assert c["router"]["definite_min"] == definite_min
    for cat, o in c["category_overrides"].items():
        if "floor_min_score" in o:
            assert o["floor_min_score"] >= review_min, cat
