"""Pillow typography renderer with relative line-progress karaoke fill."""
from __future__ import annotations
from pathlib import Path
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_NAMES={
 "sans":["DejaVuSans-Bold.ttf"],"serif":["DejaVuSerif.ttf"],
 "script":["Pacifico-Regular.ttf","DejaVuSerif-Italic.ttf"],
 "handwriting":["KaushanScript-Regular.ttf","DejaVuSans-Oblique.ttf"],
 "display":["Bungee-Regular.ttf","DejaVuSans-Bold.ttf"],
 "mono":["DejaVuSansMono.ttf"]}
def font_for(style,size):
    # Only bundled / system allowlisted paths; do not accept arbitrary user paths.
    roots=[Path(__file__).resolve().parents[1]/"assets"/"fonts",
           Path("/usr/share/fonts/truetype/dejavu")]
    for name in FONT_NAMES[style]:
        for folder in roots:
            p=folder/name
            if p.is_file():return ImageFont.truetype(str(p),size)
    return ImageFont.load_default()

class LyricRenderer:
    def __init__(self,cues):
        self.cues=[c.validate() for c in cues]
    def apply(self,frame,state):
        active=next((c for c in self.cues if c.start<=state.t<c.end),None)
        if active is None:return frame
        cue=active;h,w=frame.shape[:2]
        signal=max(0,min(1,float(getattr(state,cue.signal,0))))
        font=font_for(cue.font,max(18,int(w*.052*(1+.12*signal if cue.bounce else 1))))
        layer=Image.new("RGBA",(w,h))
        draw=ImageDraw.Draw(layer)
        # Break long lines by measured pixels, not character count.
        lines=[];part=""
        for word in cue.text.split():
            test=(part+" "+word).strip()
            if draw.textbbox((0,0),test,font=font,stroke_width=3)[2]>w*.86 and part:
                lines.append(part);part=word
            else:part=test
        if part:lines.append(part)
        lines=lines[:4]
        if not lines:return frame
        y=int(h*{"top":.12,"middle":.43,"bottom":.77}[cue.position])
        step=max(24,int(w*.066))
        progress=max(0,min(1,(state.t-cue.start)/(cue.end-cue.start)))
        if cue.words:
            # Time-based progression through each spoken word rather than linear line duration.
            lengths=[len(str(word[0]))+1 for word in cue.words]
            weighted_total=sum(lengths)
            elapsed=sum(length*max(0,min(1,(state.t-float(word[1]))/(float(word[2])-float(word[1]))))
                        for word,length in zip(cue.words,lengths))
            progress=elapsed/max(1,weighted_total)
        for row,line in enumerate(lines):
            bbox=draw.textbbox((0,0),line,font=font,stroke_width=3)
            tw=bbox[2]-bbox[0]; x=max(0,(w-tw)//2)
            yy=min(h-step,y+step*row)
            if cue.glow:
                for radius in (7,4):
                    draw.text((x,yy),line,font=font,fill=cue.highlight+"35",
                              stroke_width=radius,stroke_fill=cue.highlight+"35")
            draw.text((x,yy),line,font=font,fill=cue.color,stroke_width=2,stroke_fill=cue.outline)
            # Karaoke fill is clipped to the segment of text already performed.
            if cue.style=="karaoke":
                text_layer=Image.new("RGBA",(w,h))
                d=ImageDraw.Draw(text_layer)
                d.text((x,yy),line,font=font,fill=cue.highlight,stroke_width=1,stroke_fill=cue.outline)
                mask=Image.new("L",(w,h),0)
                ImageDraw.Draw(mask).rectangle((x,yy,x+int(tw*progress),min(h,yy+step*2)),fill=255)
                layer.paste(text_layer,(0,0),mask)
        base=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).convert("RGBA")
        out=Image.alpha_composite(base,layer).convert("RGB")
        return cv2.cvtColor(np.asarray(out),cv2.COLOR_RGB2BGR)
