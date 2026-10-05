import numpy as np
from beatstudio.narrative import NarrativePlan, NarrativeSection, narrative_scene_score
from beatstudio.scene_understanding import SceneProfile

def test_narrative_scene_prefers_matching_tags():
    section=NarrativeSection(
        index=0,start=0,end=10,label="Chorus",intent="",
        preferred_tags=["dancing","performance","wide"],
        avoid_tags=[],shot_scale="wide",motion_style="",emotional_tone="",
        pacing="fast",effect_direction=[],seedance_prompt="",energy=.8,drop_peak=.9
    )
    dance=SceneProfile(path="a",dancing=.9,performers=.8,wide=.8,motion=.8)
    calm=SceneProfile(path="b",landscapes=.8,closeup=.7,motion=.1)
    assert narrative_scene_score(dance,section) > narrative_scene_score(calm,section)

def test_plan_section_lookup():
    sections=[
        NarrativeSection(0,0,10,"Intro","",[],[],"wide","","","slow",[],"",.2,.1),
        NarrativeSection(1,10,20,"Verse","",[],[],"close","","","medium",[],"",.4,.2),
    ]
    plan=NarrativePlan(20,120,"arc",sections)
    assert plan.section_at(5).label=="Intro"
    assert plan.section_at(15).label=="Verse"
