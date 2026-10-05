from __future__ import annotations

import numpy as np
import librosa
import soundfile as sf

class SoundFXEngine:
    def __init__(self,audio_path,sr=44100):
        self.audio_path=audio_path
        self.y,self.sr=librosa.load(audio_path,sr=sr,mono=True)

    def _impact(self,duration=.45):
        n=int(duration*self.sr); t=np.arange(n)/self.sr
        low=np.sin(2*np.pi*(72-35*t)*t)*np.exp(-8*t)
        noise=np.random.default_rng(42).normal(0,1,n)*np.exp(-12*t)
        return .7*low+.18*noise

    def _whoosh(self,duration=.9):
        n=int(duration*self.sr); t=np.arange(n)/self.sr
        rng=np.random.default_rng(123)
        noise=rng.normal(0,1,n)
        env=np.sin(np.pi*np.clip(t/duration,0,1))**1.7
        # emphasize changing high-frequency content using a simple first difference
        bright=np.r_[0,np.diff(noise)]
        return .22*bright*env

    def _riser(self,duration=1.4):
        n=int(duration*self.sr); t=np.arange(n)/self.sr
        f0,f1=120,900
        phase=2*np.pi*(f0*t+(f1-f0)/(2*duration)*t*t)
        env=np.clip(t/duration,0,1)**1.4
        return .16*np.sin(phase)*env

    @staticmethod
    def _mix_at(base,clip,index,gain=1.0):
        if index>=len(base): return
        end=min(len(base),index+len(clip))
        base[index:end]+=clip[:end-index]*gain

    def render(self,output_path,*,drop_times=None,section_times=None,add_risers=True):
        out=self.y.astype(np.float32).copy()
        for t in drop_times or []:
            self._mix_at(out,self._impact(),int(float(t)*self.sr),.75)
        for t in section_times or []:
            idx=max(0,int(float(t)*self.sr))
            self._mix_at(out,self._whoosh(),idx,.55)
            if add_risers:
                riser=self._riser()
                self._mix_at(out,riser,max(0,idx-len(riser)),.65)
        peak=max(1.0,float(np.max(np.abs(out)))/.97)
        out/=peak
        sf.write(output_path,out,self.sr)
        return output_path
