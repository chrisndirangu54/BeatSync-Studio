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
    '4k_export','batch_export','preset_save','commercial_use','priority_render',
    'auto_director','scene_understanding','auto_sound_fx',
    'suno_generation','suno_editing','ai_dj','licensed_catalog',
    'seedance_generation','stock_video','project_history','team_projects'
})

PLANS: Dict[str, Plan] = {
    'free': Plan(
        'free','Free',0,720,True,5,1,
        frozenset({'basic_sync','auto_director','stock_video'})
    ),
    'pro': Plan(
        'pro','Pro',19,1080,False,18,2,
        frozenset({
            'basic_sync','advanced_sync','neural_segmentation','preset_save',
            'auto_director','scene_understanding','suno_generation','ai_dj',
            'licensed_catalog','stock_video','auto_sound_fx'
        })
    ),
    'creator': Plan(
        'creator','Creator',39,2160,False,999,3,
        frozenset({
            'basic_sync','advanced_sync','section_detection','neural_segmentation',
            'optical_flow','4k_export','preset_save','commercial_use',
            'auto_director','scene_understanding','auto_sound_fx',
            'suno_generation','suno_editing','ai_dj','licensed_catalog',
            'seedance_generation','stock_video','project_history'
        })
    ),
    'studio': Plan('studio','Studio',99,2160,False,999,3,ALL),
}

def get_plan(key: str) -> Plan:
    return PLANS.get(key, PLANS['free'])
