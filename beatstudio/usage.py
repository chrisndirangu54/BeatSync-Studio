from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class UsageQuota:
    render_minutes: int
    music_generations: int
    video_generations: int
    dj_transitions: int
    auto_director_projects: int

QUOTAS: Dict[str, UsageQuota] = {
    "free": UsageQuota(10,0,0,0,1),
    "pro": UsageQuota(180,10,0,20,20),
    "creator": UsageQuota(600,40,10,100,100),
    "studio": UsageQuota(2400,200,60,9999,9999),
}

def quota_for(plan_key: str) -> UsageQuota:
    return QUOTAS.get(plan_key, QUOTAS["free"])

def estimated_render_minutes(duration_seconds: float, export_height: int) -> float:
    resolution_multiplier=1.0
    if export_height>=2160: resolution_multiplier=4.0
    elif export_height>=1080: resolution_multiplier=1.8
    return (duration_seconds/60.0)*resolution_multiplier
