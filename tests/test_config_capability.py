import json, sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fedhomeguard import config as CFG, capability as CAP, data as DATA


def test_config_roundtrip_yaml():
    c = CFG.load("configs/stage3_certification.yaml")
    assert c.partition.kind == "device_derived" and c.cert.k == 5
    assert CFG.from_dict(c.to_dict()).to_dict() == c.to_dict()


def test_capability_record_has_required_sections_and_non_guarantees():
    c = CFG.load("configs/stage3_certification.yaml")
    r = CAP.build_record(c, run_id="t", partition_meta={"S_JS": 0.8, "kind": "device_derived"},
                         n_params=1234, malicious_ids=(1, 2), attacks_run=("ipm",))
    for sec in ("federation", "partition", "adversary", "defense", "certification",
                "budget", "seeds", "non_guarantees"):
        assert sec in r
    assert r["adversary"]["F4_knows_subsample_seed"] is False
    assert len(r["non_guarantees"]) >= 10
    assert any("sybil" in s for s in r["non_guarantees"])
    json.dumps(r)                       # must be serializable


def test_ciciot_device_attribution_raises_loudly():
    with pytest.raises(DATA.AttributionError, match="NO device identifier"):
        DATA.ciciot_device_ids(None)
    assert DATA.SUPPORTS_DEVICE_PARTITION["ciciot2023"] is False
    assert DATA.SUPPORTS_DEVICE_PARTITION["iot-23"] is True
