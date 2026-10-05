from __future__ import annotations
import os, cv2, subprocess, tempfile
from typing import Dict
from .intelligence import IntelligentBeatSync
from .effects import REGISTRY, TIER_RANK, apply_effect
from .plans import get_plan
from .auto_fx import AutoFXPolicy
from .sound_fx import SoundFXEngine

class VideoRenderer:
    def __init__(self, video_path, audio_path, output_path, plan_key='free', enabled: Dict[str,float]|None=None, automatic_fx: bool=False, automatic_sound_fx: bool=False):
        self.video_path=video_path; self.audio_path=audio_path; self.output_path=output_path
        self.plan=get_plan(plan_key); self.enabled=enabled or {}
        self.automatic_fx=automatic_fx; self.automatic_sound_fx=automatic_sound_fx
        self.sync=IntelligentBeatSync(audio_path, self.plan.intelligent_sync_level)
        self.prev_frame=None

    def validate_effects(self):
        allowed=[]
        rank=TIER_RANK[self.plan.key]
        for key,intensity in self.enabled.items():
            if key in REGISTRY and TIER_RANK[REGISTRY[key].tier] <= rank and intensity>0:
                allowed.append((key,float(intensity)))
        return allowed[:self.plan.max_effects]

    def render(self, progress=None):
        cap=cv2.VideoCapture(self.video_path)
        if not cap.isOpened(): raise RuntimeError('Could not open video')
        fps=cap.get(cv2.CAP_PROP_FPS) or 30; w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        scale=min(1.0,self.plan.export_height/max(h,1)); ow,oh=max(2,int(w*scale)//2*2),max(2,int(h*scale)//2*2)
        fd,temp=tempfile.mkstemp(suffix='.mp4'); os.close(fd)
        writer=cv2.VideoWriter(temp,cv2.VideoWriter_fourcc(*'mp4v'),fps,(ow,oh))
        effects=self.validate_effects(); idx=0; previous_section=None
        while True:
            ok,frame=cap.read()
            if not ok: break
            if (ow,oh)!=(w,h): frame=cv2.resize(frame,(ow,oh))
            state=self.sync.state(idx/fps)
            out=frame
            dynamic=[]
            if self.automatic_fx:
                decision=AutoFXPolicy.decide(state, previous_section is not None and state.section!=previous_section)
                rank=TIER_RANK[self.plan.key]
                dynamic=[(k,v) for k,v in decision.video_effects.items() if k in REGISTRY and TIER_RANK[REGISTRY[k].tier] <= rank]
            if any(k=='ghost_trail' for k,_ in effects) and self.prev_frame is not None:
                inten=dict(effects).get('ghost_trail',0); out=cv2.addWeighted(out,1-.35*inten,self.prev_frame,.35*inten,0)
            for key,intensity in effects + dynamic:
                if key!='ghost_trail': out=apply_effect(out,key,intensity,state,idx)
            previous_section=state.section
            if self.plan.watermark:
                cv2.putText(out,'BeatSync Studio • Free',(16,oh-16),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1,cv2.LINE_AA)
            self.prev_frame=out.copy(); writer.write(out); idx+=1
            if progress and idx%5==0: progress(min(1.0,idx/total))
        cap.release(); writer.release()
        mux_audio=self.audio_path
        temp_audio=None
        if self.automatic_sound_fx:
            fd,temp_audio=tempfile.mkstemp(suffix='.wav'); os.close(fd)
            curve=self.sync.drop_curve
            drop_times=[]
            for i in range(1,len(curve)-1):
                if curve[i]>.80 and curve[i]>=curve[i-1] and curve[i]>=curve[i+1]:
                    drop_times.append(i*self.sync.hop/self.sync.sr)
            section_times=[float(x) for x in self.sync.section_boundaries[1:-1]]
            SoundFXEngine(self.audio_path).render(temp_audio,drop_times=drop_times,section_times=section_times)
            mux_audio=temp_audio
        cmd=['ffmpeg','-y','-i',temp,'-i',mux_audio,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','20','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',self.output_path]
        p=subprocess.run(cmd,capture_output=True,text=True)
        try: os.remove(temp)
        except OSError: pass
        if temp_audio:
            try: os.remove(temp_audio)
            except OSError: pass
        if p.returncode!=0: raise RuntimeError(p.stderr[-3000:])
        return self.output_path
