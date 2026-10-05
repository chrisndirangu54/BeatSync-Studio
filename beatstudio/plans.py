from dataclasses import dataclass
from typing import Dict, FrozenSet

@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    monthly_usd: int
    export_height: int
    watermark: bool
    max_effects: int
    intelligent_sync_level: int
    features: FrozenSet[str]

ALL = frozenset({
    'basic_sync','advanced_sync','section_detection','neural_segmentation','optical_flow',
    '4k_export','batch_export','preset_save','commercial_use','priority_render'
})

PLANS: Dict[str, Plan] = {
    'free': Plan('free','Free',0,720,True,5,1,frozenset({'basic_sync'})),
    'pro': Plan('pro','Pro',12,1080,False,18,2,frozenset({'basic_sync','advanced_sync','neural_segmentation','preset_save'})),
    'creator': Plan('creator','Creator',29,2160,False,999,3,frozenset({'basic_sync','advanced_sync','section_detection','neural_segmentation','optical_flow','4k_export','preset_save','commercial_use'})),
    'studio': Plan('studio','Studio',79,2160,False,999,3,ALL),
}

def get_plan(key: str) -> Plan:
    return PLANS.get(key, PLANS['free'])
