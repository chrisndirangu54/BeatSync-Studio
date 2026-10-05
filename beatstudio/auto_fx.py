from dataclasses import dataclass
from typing import Dict,List

@dataclass
class AutoFXDecision:
    video_effects: Dict[str,float]
    sound_events: List[str]

class AutoFXPolicy:
    @staticmethod
    def decide(state,section_changed=False):
        fx={}; sfx=[]
        if state.beat>.45:
            fx["zoom_pulse"]=.30+.30*state.energy
            fx["pulse_border"]=.18+.22*state.brightness
        if state.onset>.60:
            fx["chromatic"]=.25+.35*state.treble
            fx["camera_shake"]=.20+.25*state.energy
        if state.bass>.70:
            fx["particles"]=.30+.30*state.bass
            fx["bloom"]=.20+.20*state.energy
        if state.treble>.75 and state.energy>.45:
            fx["glitch_slices"]=.18+.22*state.treble
        if state.drop>.76:
            fx["micro_punch"]=.65; fx["flash"]=.40; fx["confetti"]=.35; sfx.append("impact")
        if section_changed:
            fx["hue_shift"]=.40; sfx.append("whoosh")
        if state.energy<.25:
            fx["vignette"]=.28; fx["film_grain"]=.16
        return AutoFXDecision(video_effects=fx,sound_events=sfx)
