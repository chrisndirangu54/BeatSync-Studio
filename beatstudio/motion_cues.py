"""Independent time-coded motion-graphic and reaction overlays.

Deterministic renderer for curated content; provider-generated scripts/assets can
be reviewed and converted to cue data before rendering.
"""
from dataclasses import dataclass
import math
import cv2
import numpy as np

@dataclass(frozen=True)
class MotionCue:
    text: str
    start: float
    duration: float = 2.0
    style: str = "explainer"
    trigger: str = "beat"
    position: str = "bottom"

    def validate(self):
        if not isinstance(self.text,str) or not 1 <= len(self.text) <= 140:
            raise ValueError("Cue text must have 1–140 characters")
        if not 0 <= self.start <= 600 or not .2 <= self.duration <= 30:
            raise ValueError("Invalid cue timing")
        if self.style not in {"explainer","reaction","lower_third","stat","title"}:
            raise ValueError("Invalid cue style")
        if self.trigger not in {"beat","bass","mids","treble","onset","drop","energy"}:
            raise ValueError("Invalid cue trigger")
        if self.position not in {"top","middle","bottom"}:
            raise ValueError("Invalid cue position")
        return self

class CueRenderer:
    def __init__(self,cues):
        self.cues=[c.validate() for c in cues]
    def apply(self,frame,state):
        active=[c for c in self.cues if c.start <= state.t < c.start+c.duration]
        if not active: return frame
        out=frame.copy()
        h,w=out.shape[:2]
        for cue in active[:3]:
            progress=(state.t-cue.start)/cue.duration
            eased=min(1,progress/.12,(1-progress)/.12)
            beat=float(np.clip(getattr(state,cue.trigger,0),0,1))
            opacity=max(0,min(1,eased))*(.65+.35*beat)
            base={"top":.18,"middle":.51,"bottom":.83}[cue.position]
            baseline=int(h*base)
            font_scale=min(1.25,max(.48,w/1050))
            text=cue.text.replace("\n"," ")[:140]
            # Wrap long overlays so they do not overflow the output frame.
            max_chars=max(12,int(w/(font_scale*22)))
            words=text.split()
            lines=[];line=""
            for word in words:
                if len(line)+len(word)+1>max_chars and line:
                    lines.append(line);line=word
                else: line=(line+" "+word).strip()
            if line:lines.append(line)
            lines=lines[:3]
            block_height=round(45*font_scale*(len(lines)+1))
            y=max(2,min(h-block_height-2,baseline-block_height))
            x=int(w*.06)
            panel=out.copy()
            cv2.rectangle(panel,(x-12,y-15),(min(w-2,w-x+12),y+block_height),(18,10,28),-1)
            out=cv2.addWeighted(out,1-opacity*.72,panel,opacity*.72,0)
            color=(255,90,255) if cue.style=="reaction" else (255,255,70)
            for n,line in enumerate(lines):
                cv2.putText(out,line,(x,y+int((n+1)*38*font_scale)),
                            cv2.FONT_HERSHEY_SIMPLEX,font_scale,color,2,cv2.LINE_AA)
            if cue.style in {"explainer","stat"}:
                cv2.line(out,(x,y-5),(min(w-4,x+int(w*.24*opacity)),y-5),
                         (255,220,40),4,cv2.LINE_AA)
        return out
