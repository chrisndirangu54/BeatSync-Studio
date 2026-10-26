"""Explicit skeleton mapping and deterministic motion planning.

No inference model is falsely claimed here. Source/target rig metadata can be
provided by a dedicated motion model worker; these mappings enforce constraints.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Mapping

HUMAN_BONES=("hips","spine","chest","neck","head","left_upper_arm","left_forearm",
             "left_hand","right_upper_arm","right_forearm","right_hand",
             "left_thigh","left_shin","left_foot","right_thigh","right_shin","right_foot")
QUADRUPED_BONES=("root","spine","neck","head","front_left_upper","front_left_lower",
                 "front_right_upper","front_right_lower","hind_left_upper","hind_left_lower",
                 "hind_right_upper","hind_right_lower","tail")
ALIASES={"hips":("Hips","mixamorig:Hips","pelvis","Pelvis"),
         "spine":("Spine","mixamorig:Spine","spine_01"),
         "chest":("Spine2","mixamorig:Spine2","chest","spine_03"),
         "neck":("Neck","mixamorig:Neck","neck_01"),
         "head":("Head","mixamorig:Head","head")}
def canonical(name):
    s=name.lower().replace("mixamorig:","").replace("_","").replace(" ","")
    return s

def infer_mapping(source_bones, target_bones, *, species="human"):
    """Return explicit matched bone names; never guess missing critical joints."""
    if species not in {"human","quadruped"}: raise ValueError("Unsupported mapping family")
    source={canonical(x):x for x in source_bones}
    target={canonical(x):x for x in target_bones}
    pairs={}
    for key in (HUMAN_BONES if species=="human" else QUADRUPED_BONES):
        candidates=[key]+list(ALIASES.get(key,()))
        sm=next((source[canonical(c)] for c in candidates if canonical(c) in source),None)
        tm=next((target[canonical(c)] for c in candidates if canonical(c) in target),None)
        if sm and tm:pairs[sm]=tm
    return pairs

@dataclass(frozen=True)
class RetargetSpec:
    species: str = "human"
    source_armature: str = ""
    target_armature: str = ""
    mapping: tuple[tuple[str,str],...] = ()
    preserve_root: bool = True
    scale_translation: bool = True
    def validate(self):
        if self.species not in {"human","quadruped"}:raise ValueError("Unsupported species")
        if len(self.mapping)>128:raise ValueError("Too many mapped bones")
        source=[x for x,y in self.mapping];target=[y for x,y in self.mapping]
        if len(set(source))!=len(source) or len(set(target))!=len(target):
            raise ValueError("Bone mappings must be one-to-one")
        if any(not x or not y or len(x)>100 or len(y)>100 for x,y in self.mapping):
            raise ValueError("Invalid bone names")
        return self
    def manifest(self):return asdict(self.validate())

def dance_timing(beat_times, *, bpm=120., speed=1., duration=10.):
    if not 20<=bpm<=300 or not .1<=speed<=4 or not 0<duration<=600:
        raise ValueError("Invalid timing")
    if beat_times:
        values=sorted(set(float(t) for t in beat_times if 0<=t<=duration))
    else:
        values=[i*60/bpm for i in range(int(duration*bpm/60)+1)]
    return [{"t":round(t,5),"speed":speed,"accent":(i%4==0)} for i,t in enumerate(values)]
