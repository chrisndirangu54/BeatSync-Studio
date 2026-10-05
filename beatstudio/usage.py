from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class UsageQuota:
    render_minutes: int
    music_generations: int
    auto_director_projects: int


QUOTAS: Dict[str, UsageQuota] = {
    "free": UsageQuota(render_minutes=10, music_generations=0, auto_director_projects=1),
    "pro": UsageQuota(render_minutes=180, music_generations=10, auto_director_projects=20),
    "creator": UsageQuota(render_minutes=600, music_generations=40, auto_director_projects=100),
    "studio": UsageQuota(render_minutes=2400, music_generations=200, auto_director_projects=9999),
}


def quota_for(plan_key: str) -> UsageQuota:
    return QUOTAS.get(plan_key, QUOTAS["free"])


def estimated_render_minutes(duration_seconds: float, export_height: int) -> float:
    """
    A simple billing unit. 4K costs more because it consumes far more compute.
    This is intentionally transparent and can later be replaced by GPU-second
    metering from workers.
    """
    resolution_multiplier = 1.0
    if export_height >= 2160:
        resolution_multiplier = 4.0
    elif export_height >= 1080:
        resolution_multiplier = 1.8
    return (duration_seconds / 60.0) * resolution_multiplier
