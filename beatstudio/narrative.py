from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import numpy as np

from .intelligence import IntelligentBeatSync


@dataclass
class NarrativeSection:
    index: int
    start: float
    end: float
    label: str
    intent: str
    preferred_tags: List[str]
    avoid_tags: List[str]
    shot_scale: str
    motion_style: str
    emotional_tone: str
    pacing: str
    effect_direction: List[str]
    seedance_prompt: str
    energy: float
    drop_peak: float

    def to_dict(self):
        return asdict(self)


@dataclass
class NarrativePlan:
    duration: float
    tempo: float
    arc: str
    sections: List[NarrativeSection]

    def section_at(self, t: float) -> NarrativeSection:
        for section in self.sections:
            if section.start <= t < section.end:
                return section
        return self.sections[-1]

    def to_dict(self):
        return {
            "duration": self.duration,
            "tempo": self.tempo,
            "arc": self.arc,
            "sections": [s.to_dict() for s in self.sections],
        }


class NarrativePlanner:
    """
    Turns song structure into an editorial story plan before shot selection.

    This is intentionally deterministic and inspectable: it derives section-level
    energy/drop summaries from IntelligentBeatSync, then assigns a cinematic role.
    A future LLM can refine the labels/briefs without changing the director contract.
    """

    def __init__(self, audio_path: str, intelligence_level: int = 3):
        self.sync = IntelligentBeatSync(audio_path, max(3, intelligence_level))

    def _window_mean(self, arr, start: float, end: float) -> float:
        a = int(np.clip(start * self.sync.sr / self.sync.hop, 0, len(arr)-1))
        b = int(np.clip(end * self.sync.sr / self.sync.hop, a+1, len(arr)))
        return float(np.mean(arr[a:b])) if b > a else float(arr[a])

    def _window_max(self, arr, start: float, end: float) -> float:
        a = int(np.clip(start * self.sync.sr / self.sync.hop, 0, len(arr)-1))
        b = int(np.clip(end * self.sync.sr / self.sync.hop, a+1, len(arr)))
        return float(np.max(arr[a:b])) if b > a else float(arr[a])

    @staticmethod
    def _role(index: int, total: int, energy: float, drop: float, previous_energy: float) -> str:
        if index == 0:
            return "intro"
        if index == total - 1:
            return "finale"
        if drop > .80:
            return "chorus" if index < total - 2 else "final_drop"
        rise = energy - previous_energy
        if rise > .18:
            return "pre_chorus"
        if energy < .28:
            return "bridge"
        if energy > .68:
            return "chorus"
        return "verse"

    @staticmethod
    def _brief(role: str, energy: float, drop: float) -> Dict[str, object]:
        if role == "intro":
            return dict(
                intent="Establish place, mood and visual world before revealing too much.",
                preferred_tags=["landscape","wide","calm","city","atmospheric"],
                avoid_tags=["confetti","extreme motion"],
                shot_scale="wide",
                motion_style="slow push, drift or locked-off establishing frames",
                emotional_tone="mysterious / anticipatory",
                pacing="slow",
                effect_direction=["film_grain","vignette","subtle_bloom"],
            )
        if role == "verse":
            return dict(
                intent="Build connection with the performer and story while preserving space for the chorus.",
                preferred_tags=["performance","closeup","faces","medium","calm"],
                avoid_tags=["maximum motion"],
                shot_scale="close / medium",
                motion_style="controlled handheld, gentle movement, selective cutaways",
                emotional_tone="intimate / narrative",
                pacing="medium",
                effect_direction=["neon_edges","light_leak","subtle_zoom"],
            )
        if role == "pre_chorus":
            return dict(
                intent="Create visual acceleration and expectation before the release.",
                preferred_tags=["performance","motion","wide","dancing"],
                avoid_tags=["static landscape"],
                shot_scale="medium → wide",
                motion_style="increasing movement, shorter shots, camera push-ins",
                emotional_tone="rising tension",
                pacing="accelerating",
                effect_direction=["zoom_pulse","bloom","chromatic"],
            )
        if role == "chorus":
            return dict(
                intent="Deliver the primary performance payoff and strongest recognizable visual motif.",
                preferred_tags=["dancing","performance","wide","motion","joyful","cars"],
                avoid_tags=["static calm closeups"],
                shot_scale="wide + hero closeups",
                motion_style="dynamic, beat-emphasized, confident camera movement",
                emotional_tone="release / power / celebration",
                pacing="fast",
                effect_direction=["particles","camera_shake","bloom","pulse_border"],
            )
        if role == "bridge":
            return dict(
                intent="Reset contrast, reveal vulnerability or a new visual idea before the final build.",
                preferred_tags=["closeup","faces","sad","calm","landscape"],
                avoid_tags=["confetti","rapid cuts"],
                shot_scale="close",
                motion_style="minimal movement, longer takes",
                emotional_tone="reflective / emotional",
                pacing="slow",
                effect_direction=["vignette","duotone","film_grain"],
            )
        if role == "final_drop":
            return dict(
                intent="Create the most memorable hero sequence of the video.",
                preferred_tags=["dancing","performance","motion","wide","cars","intense"],
                avoid_tags=[],
                shot_scale="hero wide + extreme closeups",
                motion_style="maximum controlled energy, bold angle changes, impact cuts",
                emotional_tone="climactic / triumphant",
                pacing="very fast",
                effect_direction=["micro_punch","flash","confetti","chromatic","bloom"],
            )
        return dict(
            intent="Resolve the visual story with a final iconic image.",
            preferred_tags=["performance","wide","landscape","closeup"],
            avoid_tags=[],
            shot_scale="wide or intimate final closeup",
            motion_style="decelerate toward a strong ending frame",
            emotional_tone="resolution",
            pacing="decelerating",
            effect_direction=["bloom","vignette"],
        )

    @staticmethod
    def _seedance_prompt(role: str, preferred_tags: List[str], tone: str, motion_style: str) -> str:
        subject = ", ".join(preferred_tags[:3])
        return (
            f"Music video hero shot for a {role.replace('_',' ')} section. "
            f"Visual focus: {subject}. Emotional tone: {tone}. "
            f"Camera language: {motion_style}. Cinematic lighting, coherent performer identity, "
            f"premium music-video production, no text or logos."
        )

    def plan(self) -> NarrativePlan:
        boundaries = self.sync.section_boundaries
        if len(boundaries) < 2:
            boundaries = np.array([0.0, self.sync.duration])

        metrics = []
        for i in range(len(boundaries)-1):
            start, end = float(boundaries[i]), float(boundaries[i+1])
            metrics.append((
                self._window_mean(self.sync.rms, start, end),
                self._window_max(self.sync.drop_curve, start, end),
            ))

        sections = []
        previous_energy = metrics[0][0] if metrics else 0.0
        total = len(metrics)
        for i, ((energy, drop), start, end) in enumerate(zip(metrics, boundaries[:-1], boundaries[1:])):
            role = self._role(i, total, energy, drop, previous_energy)
            brief = self._brief(role, energy, drop)
            seedance_prompt = self._seedance_prompt(
                role,
                brief["preferred_tags"],
                brief["emotional_tone"],
                brief["motion_style"],
            )
            sections.append(NarrativeSection(
                index=i,
                start=float(start),
                end=float(end),
                label=role.replace("_"," ").title(),
                intent=brief["intent"],
                preferred_tags=list(brief["preferred_tags"]),
                avoid_tags=list(brief["avoid_tags"]),
                shot_scale=brief["shot_scale"],
                motion_style=brief["motion_style"],
                emotional_tone=brief["emotional_tone"],
                pacing=brief["pacing"],
                effect_direction=list(brief["effect_direction"]),
                seedance_prompt=seedance_prompt,
                energy=float(energy),
                drop_peak=float(drop),
            ))
            previous_energy = energy

        arc = "establish → connect → build → release → contrast → climax → resolve"
        return NarrativePlan(
            duration=float(self.sync.duration),
            tempo=float(self.sync.tempo),
            arc=arc,
            sections=sections,
        )


def narrative_scene_score(profile, section: NarrativeSection) -> float:
    score = 0.0
    tag_values = {
        "performance": profile.performers,
        "dancing": profile.dancing,
        "cars": profile.cars,
        "landscape": profile.landscapes,
        "closeup": profile.closeup,
        "wide": profile.wide,
        "motion": profile.motion,
        "faces": profile.faces,
        "joyful": profile.emotion.get("joyful",0.0),
        "sad": profile.emotion.get("sad",0.0),
        "intense": profile.emotion.get("intense",0.0),
        "calm": profile.emotion.get("calm",0.0),
        "medium": .5 * profile.people + .5 * (1.0 - abs(profile.closeup-profile.wide)),
        "city": 0.0,
        "atmospheric": .5 * profile.landscapes + .5 * profile.wide,
    }
    for rank, tag in enumerate(section.preferred_tags):
        score += tag_values.get(tag,0.0) * (0.28 / (1 + rank*.35))
    for tag in section.avoid_tags:
        score -= tag_values.get(tag,0.0) * .18
    if section.shot_scale.startswith("wide"):
        score += .15 * profile.wide
    if section.shot_scale.startswith("close"):
        score += .15 * profile.closeup
    if section.pacing in {"fast","very fast","accelerating"}:
        score += .12 * profile.motion
    if section.pacing == "slow":
        score += .10 * (1.0-profile.motion)
    return float(score)
