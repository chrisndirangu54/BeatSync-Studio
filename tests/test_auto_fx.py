from beatstudio.auto_fx import AutoFXPolicy
from beatstudio.intelligence import BeatState

def test_drop_triggers_impact_and_visual_punch():
    state=BeatState(t=1,beat=1,onset=1,bass=1,mids=.4,treble=.6,energy=.9,brightness=.6,drop=.95,section=1)
    decision=AutoFXPolicy.decide(state)
    assert "impact" in decision.sound_events
    assert "micro_punch" in decision.video_effects
