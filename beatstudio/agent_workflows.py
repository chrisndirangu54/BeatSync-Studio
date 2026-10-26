"""Deterministic, auditable prompt-to-edit specialist agent workflow.

The pipeline is deliberately non-executing. Its output consists only of bounded
application-native configuration. Prompts are data, never code or shell commands.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from .blender_simulations import SimulationLayer
from .motion_cues import MotionCue
from .lyrics import LyricCue

AGENTS=("director","rhythm","visual_fx","typography","quality")
COLORS={"cyan":"#00FFFF","magenta":"#FF40FF","lime":"#8AFF00","gold":"#FFD166","blue":"#528BFF","white":"#FFFFFF"}
SUPPORTED_EFFECTS={"neon_particles","spectrum_bars","radial_spectrum","wave_tunnel","neon_fireworks","shockwave"}
STYLES={"karaoke","calligraphy","brush","neon_script","serif","bold_pop","gothic","minimal"}
@dataclass(frozen=True)
class WorkflowStep:
    agent:str
    action:str
    rationale:str
    output:dict
    def manifest(self):return asdict(self)

def plan_prompt(prompt:str, *, duration:float=30, intensity:float=.7):
    if not isinstance(prompt,str) or not 3<=len(prompt.strip())<=2000:
        raise ValueError("Prompt must contain 3–2000 characters")
    if not isinstance(duration,(int,float)) or not 1<=duration<=600:
        raise ValueError("Duration must be 1–600 seconds")
    if not isinstance(intensity,(int,float)) or not 0<=intensity<=1:
        raise ValueError("Intensity must be 0–1")
    p=prompt.lower()
    steps=[]
    def step(agent,action,rationale,output):
        steps.append(WorkflowStep(agent,action,rationale,output).manifest())
    mood="cinematic" if any(s in p for s in ("cinematic","film","dramatic")) else "energetic" if any(s in p for s in ("dance","party","hype","fast","club")) else "balanced"
    step("director","set_direction","Extracts creative direction without executing arbitrary prompt commands",{"mood":mood,"duration":float(duration)})
    signal="bass" if any(s in p for s in ("bass","drum","kick","drop")) else "onset" if any(s in p for s in ("snare","clap","hit")) else "beat"
    step("rhythm","select_signal","Selects an existing BeatSync audio feature",{"signal":signal})
    effect="spectrum_bars" if any(s in p for s in ("spectrum","equalizer","bars")) else "neon_fireworks" if "firework" in p else "shockwave" if "shockwave" in p else "wave_tunnel" if "tunnel" in p else "neon_particles"
    hue=next((color for color in COLORS if color in p),"cyan")
    second="magenta" if hue!="magenta" else "blue"
    layer=SimulationLayer(effect,signal=signal,intensity=float(intensity),color_a=hue if hue in ("cyan","magenta","blue","lime") else "cyan",color_b=second).validate()
    step("visual_fx","configure_layer","Applies a bounded Blender preset and vetted palette",{"blender_layers":[layer.manifest()]})
    text_match=re.search(r'(?:show|display|write|title|caption)\s+[\\"\'“]?(.{1,100}?)[\\"\'”]?(?:[.!?]|$)',prompt,re.I)
    caption=(text_match.group(1).strip(" \"'“”") if text_match else "")
    if caption:
        cue=MotionCue(text=caption[:100],start=0,duration=min(4,float(duration)),style="title",trigger=signal,position="middle").validate()
        step("typography","add_title","Provides editable timecoded title rather than inventing lyrics",{"motion_cues":[asdict(cue)]})
    font_style="calligraphy" if any(s in p for s in ("calligraphy","cursive","script")) else "neon_script" if "neon" in p else "karaoke"
    step("typography","set_lyrics_theme","Uses an editable style template; no lyrics are fabricated",{"lyric_theme":{"style":font_style,"font":"script" if font_style!="karaoke" else "sans","color":COLORS.get(hue,"#FFFFFF"),"highlight":"#FF40FF","signal":signal}})
    step("quality","validate","Reviewable plan, no provider calls, file reads, or automatic render submission",{"requires_user_review":True,"effects_count":1,"agent_count":len(AGENTS)})
    return {"prompt":prompt,"steps":steps,"config":{"blender_layers":[layer.manifest()],"motion_cues":[asdict(cue)] if caption else [],"lyric_theme":{"style":font_style,"font":"script" if font_style!="karaoke" else "sans","color":COLORS.get(hue,"#FFFFFF"),"highlight":"#FF40FF","signal":signal},"automatic_fx":True},"status":"ready_for_review"}
