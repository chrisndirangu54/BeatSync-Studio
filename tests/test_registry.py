from beatstudio.effects import REGISTRY, SPECS
from beatstudio.plans import PLANS

def test_registry_unique():
    assert len(REGISTRY)==len(SPECS)

def test_plan_order():
    assert PLANS['free'].monthly_usd < PLANS['pro'].monthly_usd < PLANS['creator'].monthly_usd < PLANS['studio'].monthly_usd
