from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict
import cv2, numpy as np, random, math
from .intelligence import BeatState

@dataclass(frozen=True)
class EffectSpec:
    key: str
    name: str
    category: str
    description: str
    tier: str = 'free'
    default_intensity: float = 0.6
    signal: str = 'beat'

SPECS = [
EffectSpec('neon_edges','Neon Edges','Subject','Electric edge enhancement','free',.65,'beat'),
EffectSpec('body_aura','Body Aura','Subject','Glowing aura around segmented people','pro',.7,'energy'),
EffectSpec('silhouette_fill','Silhouette Fill','Subject','Beat-reactive silhouette tint','pro',.5,'bass'),
EffectSpec('eye_glow','Eye Glow','Subject','Bright eye pulse overlay','pro',.55,'onset'),
EffectSpec('ghost_trail','Ghost Trail','Motion','Echo-like frame trail','pro',.5,'energy'),
EffectSpec('motion_smear','Motion Smear','Motion','Directional motion blur','free',.45,'bass'),
EffectSpec('camera_shake','Camera Shake','Motion','Impact shake on transients','free',.45,'onset'),
EffectSpec('zoom_pulse','Zoom Pulse','Motion','Beat-synchronized zoom','free',.55,'beat'),
EffectSpec('micro_punch','Micro Punch','Motion','Short hard zoom on drops','creator',.65,'drop'),
EffectSpec('rotation_kick','Rotation Kick','Motion','Tiny rotational impulse','creator',.35,'onset'),
EffectSpec('chromatic','Chromatic Split','Glitch','RGB channel separation','free',.5,'onset'),
EffectSpec('glitch_slices','Glitch Slices','Glitch','Horizontal displaced strips','pro',.55,'treble'),
EffectSpec('digital_blocks','Digital Blocks','Glitch','Datamosh-inspired block offsets','creator',.5,'drop'),
EffectSpec('scanlines','Scanlines','Glitch','CRT scanline texture','free',.35,'energy'),
EffectSpec('vhs_noise','VHS Noise','Glitch','Analog static and tape noise','pro',.4,'treble'),
EffectSpec('scan_beam','Scan Beam','Glitch','Moving luminous scan beam','creator',.45,'beat'),
EffectSpec('flash','White Flash','Light','Transient white flash','free',.4,'onset'),
EffectSpec('bloom','Bloom','Light','Highlight light bleed','free',.5,'energy'),
EffectSpec('light_leak','Light Leak','Light','Animated edge light leak','pro',.45,'energy'),
EffectSpec('pulse_border','Pulse Border','Light','Beat-reactive luminous frame','pro',.55,'beat'),
EffectSpec('strobe','Smart Strobe','Light','Energy-gated strobe','creator',.35,'drop'),
EffectSpec('lens_orb','Lens Orb','Light','Synthetic lens flare orb','creator',.35,'brightness'),
EffectSpec('particles','Particles','Particles','Floating beat-reactive sparks','free',.6,'beat'),
EffectSpec('starfield','Starfield','Particles','Treble-reactive stars','pro',.45,'treble'),
EffectSpec('digital_rain','Digital Rain','Particles','Code-like falling streaks','creator',.4,'treble'),
EffectSpec('confetti','Beat Confetti','Particles','Color bursts on strong drops','creator',.5,'drop'),
EffectSpec('film_grain','Film Grain','Texture','Cinematic grain','free',.25,'energy'),
EffectSpec('posterize','Posterize','Texture','Reduced color bands','pro',.45,'beat'),
EffectSpec('halftone','Halftone','Texture','Comic-print dot texture','creator',.4,'mids'),
EffectSpec('emboss','Emboss','Texture','Relief-like edge lighting','creator',.35,'onset'),
EffectSpec('solarize','Solarize','Color','Partial tonal inversion','pro',.45,'drop'),
EffectSpec('invert_hit','Invert Hit','Color','Instant negative-color impact','pro',.5,'onset'),
EffectSpec('duotone','Duotone','Color','Two-tone music-reactive grade','pro',.5,'energy'),
EffectSpec('hue_shift','Hue Shift','Color','Dynamic hue rotation','creator',.45,'section'),
EffectSpec('teal_orange','Teal & Orange','Color','Cinematic grade','free',.4,'energy'),
EffectSpec('thermal','Thermal Vision','Color','Heatmap-like color mapping','creator',.5,'drop'),
EffectSpec('vignette','Vignette','Lens','Darkened cinematic edges','free',.4,'energy'),
EffectSpec('fisheye_pulse','Fisheye Pulse','Lens','Radial warp on beats','creator',.35,'beat'),
EffectSpec('mirror','Mirror','Geometry','Horizontal mirror blend','pro',.4,'section'),
EffectSpec('kaleidoscope','Kaleidoscope','Geometry','Symmetric quadrant reflection','creator',.45,'drop'),
EffectSpec('split_screen','Split Screen','Geometry','Offset mirrored panels','creator',.45,'beat'),
EffectSpec('beat_bars','Beat Bars','HUD','Audio-reactive side meters','pro',.55,'bass'),
EffectSpec('hud_ring','HUD Ring','HUD','Circular pulse HUD','creator',.5,'beat'),
EffectSpec('wave_line','Wave Line','HUD','Animated pseudo-waveform line','creator',.45,'mids'),
EffectSpec('timecode','Timecode','HUD','Minimal music-video timecode','pro',.35,'energy'),
]
REGISTRY = {s.key:s for s in SPECS}
TIER_RANK = {'free':0,'pro':1,'creator':2,'studio':3}

def signal_value(state: BeatState, name: str) -> float:
    if name == 'section': return ((state.section % 4)+1)/4
    return float(getattr(state, name, state.beat))

def _blend(a,b,alpha): return cv2.addWeighted(a,1-alpha,b,alpha,0)

def apply_effect(frame, key: str, intensity: float, state: BeatState, frame_idx: int=0):
    if intensity <= 0: return frame
    s = np.clip(signal_value(state, REGISTRY[key].signal),0,1)
    amount = float(np.clip(intensity*(0.25+0.75*s),0,1))
    h,w = frame.shape[:2]
    if key=='zoom_pulse' or key=='micro_punch':
        sc=1+amount*(.07 if key=='zoom_pulse' else .12); nw,nh=max(2,int(w/sc)),max(2,int(h/sc)); x=(w-nw)//2;y=(h-nh)//2; return cv2.resize(frame[y:y+nh,x:x+nw],(w,h))
    if key=='camera_shake':
        d=max(1,int(10*amount)); dx,dy=np.random.randint(-d,d+1,2); M=np.float32([[1,0,dx],[0,1,dy]]); return cv2.warpAffine(frame,M,(w,h),borderMode=cv2.BORDER_REFLECT)
    if key=='rotation_kick':
        M=cv2.getRotationMatrix2D((w//2,h//2),(amount*4)*(-1 if frame_idx%2 else 1),1); return cv2.warpAffine(frame,M,(w,h),borderMode=cv2.BORDER_REFLECT)
    if key=='motion_smear':
        k=max(3,int(3+amount*20)); k += 1-k%2; kernel=np.zeros((k,k),np.float32); kernel[k//2,:]=1/k; return cv2.filter2D(frame,-1,kernel)
    if key=='chromatic':
        shift=max(1,int(2+amount*14)); b,g,r=cv2.split(frame); r=np.roll(r,shift,1); b=np.roll(b,-shift,1); return cv2.merge([b,g,r])
    if key=='flash': return cv2.addWeighted(frame,1-amount*.45,np.full_like(frame,255),amount*.45,0)
    if key=='invert_hit' and s>.55: return cv2.bitwise_not(frame)
    if key=='film_grain':
        noise=np.random.normal(0,4+amount*18,frame.shape).astype(np.float32); return np.clip(frame.astype(np.float32)+noise,0,255).astype(np.uint8)
    if key=='scanlines':
        out=frame.copy(); out[::4]= (out[::4].astype(np.float32)*(1-.35*amount)).astype(np.uint8); return out
    if key=='vhs_noise':
        out=frame.copy(); noise=np.random.randint(-18,19,(h,1,1)); return np.clip(out.astype(np.int16)+noise,0,255).astype(np.uint8)
    if key=='glitch_slices' or key=='digital_blocks':
        out=frame.copy(); n=2+int(10*amount); maxd=int(35*amount)+1
        for _ in range(n):
            y=random.randrange(max(1,h-2)); hh=random.randrange(2,max(3,min(40,h-y))); out[y:y+hh]=np.roll(out[y:y+hh],random.randint(-maxd,maxd),1)
        return out
    if key=='posterize':
        levels=max(2,8-int(amount*5)); step=max(1,256//levels); return ((frame//step)*step).astype(np.uint8)
    if key=='solarize':
        out=frame.copy(); th=int(130+60*(1-amount)); m=out>th; out[m]=255-out[m]; return out
    if key=='thermal':
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); cm=cv2.applyColorMap(gray,cv2.COLORMAP_TURBO); return _blend(frame,cm,.75*amount)
    if key=='teal_orange':
        f=frame.astype(np.float32); b,g,r=cv2.split(f); lum=(.114*b+.587*g+.299*r)/255; b=np.clip(b+18*(1-lum)*amount-10*lum*amount,0,255); g=np.clip(g+8*(1-lum)*amount,0,255); r=np.clip(r+20*lum*amount,0,255); return cv2.merge([b,g,r]).astype(np.uint8)
    if key=='duotone':
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).astype(np.float32)/255; lo=np.array([180,50,20],np.float32); hi=np.array([20,220,255],np.float32); duo=(lo[None,None,:]*(1-gray[...,None])+hi[None,None,:]*gray[...,None]).astype(np.uint8); return _blend(frame,duo,.7*amount)
    if key=='hue_shift':
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV); hsv[:,:,0]=(hsv[:,:,0].astype(np.int16)+int((state.section*17+frame_idx*.3)*amount))%180; return cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2BGR)
    if key=='vignette':
        xx=cv2.getGaussianKernel(w,max(1,w/2.5)); yy=cv2.getGaussianKernel(h,max(1,h/2.5)); m=yy@xx.T; m/=m.max(); m=(1-.55*amount)+(.55*amount)*m; return np.clip(frame.astype(np.float32)*m[...,None],0,255).astype(np.uint8)
    if key=='bloom':
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); mask=(gray>190).astype(np.uint8)*255; bright=cv2.bitwise_and(frame,frame,mask=mask); blur=cv2.GaussianBlur(bright,(0,0),10+20*amount); return cv2.addWeighted(frame,1,blur,.55*amount,0)
    if key=='pulse_border':
        out=frame.copy(); th=max(1,int(2+10*amount)); cv2.rectangle(out,(0,0),(w-1,h-1),(255,120,40),th); return out
    if key=='light_leak':
        overlay=np.zeros_like(frame); cx=int((math.sin(frame_idx*.03)+1)*.5*w); cv2.circle(overlay,(cx,h//2),int(max(w,h)*.45),(30,80,255),-1); overlay=cv2.GaussianBlur(overlay,(0,0),80); return cv2.addWeighted(frame,1,overlay,.25*amount,0)
    if key=='lens_orb':
        out=frame.copy(); x=int(w*(.2+.6*((math.sin(frame_idx*.025)+1)/2))); y=int(h*.25); layer=np.zeros_like(frame); cv2.circle(layer,(x,y),max(10,int(40+100*amount)),(80,180,255),-1); layer=cv2.GaussianBlur(layer,(0,0),30); return cv2.addWeighted(out,1,layer,.35*amount,0)
    if key=='particles' or key=='starfield' or key=='confetti' or key=='digital_rain':
        out=frame.copy(); n=int(8+55*amount)
        for _ in range(n):
            x=random.randrange(w); y=random.randrange(h)
            if key=='digital_rain': cv2.line(out,(x,y),(x,min(h-1,y+random.randint(5,30))),(80,255,120),1)
            else: cv2.circle(out,(x,y),random.randint(1,3 if key!='confetti' else 5),(random.randrange(80,256),random.randrange(80,256),random.randrange(80,256)),-1)
        return out
    if key=='neon_edges':
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); e=cv2.Canny(gray,80,160); col=cv2.applyColorMap(e,cv2.COLORMAP_TURBO); blur=cv2.GaussianBlur(col,(0,0),4); return cv2.addWeighted(frame,1,blur,.65*amount,0)
    if key=='silhouette_fill':
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); _,m=cv2.threshold(gray,int(100+70*(1-amount)),255,cv2.THRESH_BINARY); color=np.zeros_like(frame); color[:]=(220,40,255); color=cv2.bitwise_and(color,color,mask=m); return cv2.addWeighted(frame,1,color,.25*amount,0)
    if key=='body_aura':
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); e=cv2.Canny(gray,60,140); dil=cv2.dilate(e,np.ones((7,7),np.uint8),iterations=1); glow=cv2.GaussianBlur(cv2.cvtColor(dil,cv2.COLOR_GRAY2BGR),(0,0),12); glow[:,:,0]=np.minimum(255,glow[:,:,0]*1.4); return cv2.addWeighted(frame,1,glow,.45*amount,0)
    if key=='eye_glow':
        out=frame.copy(); return out
    if key=='ghost_trail':
        return frame
    if key=='kaleidoscope':
        q=cv2.resize(frame,(w//2,h//2)); top=np.hstack([q,cv2.flip(q,1)]); return cv2.resize(np.vstack([top,cv2.flip(top,0)]),(w,h))
    if key=='mirror': return cv2.addWeighted(frame,.5,cv2.flip(frame,1),.5,0)
    if key=='split_screen':
        left=cv2.resize(frame,(w//2,h)); right=cv2.flip(left,1); return np.hstack([left,right])[:,:w]
    if key=='emboss':
        k=np.array([[-2,-1,0],[-1,1,1],[0,1,2]],np.float32); emb=cv2.filter2D(frame,-1,k)+80; return _blend(frame,np.clip(emb,0,255).astype(np.uint8),.7*amount)
    if key=='halftone':
        small=cv2.resize(frame,(max(1,w//8),max(1,h//8)),interpolation=cv2.INTER_AREA); pix=cv2.resize(small,(w,h),interpolation=cv2.INTER_NEAREST); return _blend(frame,pix,.7*amount)
    if key=='scan_beam':
        out=frame.copy(); y=int((frame_idx*5)%max(1,h)); cv2.line(out,(0,y),(w-1,y),(255,255,255),max(1,int(2+5*amount))); return out
    if key=='strobe' and state.drop>.65 and frame_idx%2==0: return cv2.addWeighted(frame,.35,np.full_like(frame,255),.65*amount,0)
    if key=='beat_bars':
        out=frame.copy(); bh=int(h*state.bass*.7*amount); cv2.rectangle(out,(0,h-bh),(max(4,int(w*.025)),h),(80,255,255),-1); cv2.rectangle(out,(w-max(4,int(w*.025)),h-bh),(w,h),(80,255,255),-1); return out
    if key=='hud_ring':
        out=frame.copy(); r=int(min(h,w)*(.12+.08*state.beat*amount)); cv2.circle(out,(w//2,h//2),r,(255,255,255),max(1,int(2+4*amount))); return out
    if key=='wave_line':
        out=frame.copy(); pts=[]
        for x in range(0,w,max(2,w//120)):
            yy=int(h*.85 + math.sin(x*.035+frame_idx*.15)*h*.03*amount*(.2+state.mids)); pts.append([x,yy])
        cv2.polylines(out,[np.array(pts,np.int32)],False,(255,220,80),2); return out
    if key=='timecode':
        out=frame.copy(); txt=f'{state.t:07.2f}  S{state.section+1}'; cv2.putText(out,txt,(20,h-25),cv2.FONT_HERSHEY_SIMPLEX,.6,(240,240,240),1,cv2.LINE_AA); return out
    if key=='fisheye_pulse':
        yy,xx=np.indices((h,w),dtype=np.float32); cx,cy=w/2,h/2; dx=(xx-cx)/cx;dy=(yy-cy)/cy;r2=dx*dx+dy*dy; factor=1+(.15*amount)*(1-r2); mx=cx+dx*cx*factor; my=cy+dy*cy*factor; return cv2.remap(frame,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    return frame
