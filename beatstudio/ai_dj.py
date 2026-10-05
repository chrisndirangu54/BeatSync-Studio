from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os

import librosa
import numpy as np
import requests
import soundfile as sf

@dataclass
class TrackFeatures:
    bpm: float
    key_index: int
    energy: float
    brightness: float
    duration: float

@dataclass
class CatalogTrack:
    id: str
    name: str
    artist: str
    stream_url: str
    download_url: str
    page_url: str
    license_url: str
    pro_licensing: bool
    tags: List[str]

class AudioCompatibility:
    KEY_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

    @staticmethod
    def analyze(path):
        y, sr = librosa.load(path, sr=44100, mono=True)
        onset = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset, sr=sr)
        bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_index = int(np.argmax(chroma.mean(axis=1))) if chroma.size else 0
        rms = librosa.feature.rms(y=y)[0]
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        return TrackFeatures(
            bpm=bpm,
            key_index=key_index,
            energy=float(np.clip(np.mean(rms)*8.0,0,1)),
            brightness=float(np.clip(np.mean(centroid)/6000.0,0,1)),
            duration=librosa.get_duration(y=y,sr=sr),
        )

    @staticmethod
    def _tempo_distance(a,b):
        if not a or not b:
            return 1.0
        candidates=[b,b/2,b*2]
        return min(abs(a-x)/max(a,x) for x in candidates)

    @staticmethod
    def _key_distance(a,b):
        d=abs(a-b)%12
        return min(d,12-d)/6.0

    @classmethod
    def score(cls,a,b):
        return float(np.clip(
            1.0-(.50*cls._tempo_distance(a.bpm,b.bpm)+.25*cls._key_distance(a.key_index,b.key_index)+
                 .15*abs(a.energy-b.energy)+.10*abs(a.brightness-b.brightness)),
            0,1
        ))

class JamendoCatalog:
    BASE="https://api.jamendo.com/v3.0/tracks/"

    def __init__(self, client_id: Optional[str]=None):
        self.client_id=client_id or os.getenv("JAMENDO_CLIENT_ID")

    @property
    def configured(self):
        return bool(self.client_id)

    def search(self, query="", *, tags=None, speed=None, instrumental=None, gender=None, limit=20, pro_licensing=True):
        if not self.client_id:
            raise RuntimeError("JAMENDO_CLIENT_ID is not configured.")
        params={
            "client_id":self.client_id,"format":"json","limit":min(200,max(1,limit)),
            "include":"licenses musicinfo","audioformat":"mp32","order":"relevance"
        }
        if query: params["search"]=query
        if tags: params["fuzzytags"]=" ".join(tags)
        if speed: params["speed"]=speed
        if instrumental is not None: params["vocalinstrumental"]="instrumental" if instrumental else "vocal"
        if gender in {"male","female"}: params["gender"]=gender
        if pro_licensing: params["prolicensing"]="true"
        r=requests.get(self.BASE,params=params,timeout=30)
        r.raise_for_status()
        out=[]
        for x in r.json().get("results",[]):
            mi=x.get("musicinfo") or {}
            tags_out=[]
            if isinstance(mi,dict):
                raw=mi.get("tags") or {}
                if isinstance(raw,dict):
                    for vals in raw.values():
                        if isinstance(vals,list): tags_out.extend(map(str,vals))
            out.append(CatalogTrack(
                id=str(x.get("id","")),name=str(x.get("name","")),artist=str(x.get("artist_name","")),
                stream_url=str(x.get("audio","")),download_url=str(x.get("audiodownload","")),
                page_url=str(x.get("shareurl","")),license_url=str(x.get("license_ccurl","")),
                pro_licensing=bool(x.get("prolicensing",False)),tags=tags_out[:20]
            ))
        return out

class AIDJ:
    @staticmethod
    def beatmatch_crossfade(first_path,second_path,output_path,*,crossfade_seconds=8.0,tempo_match=True,key_lock=False):
        y1,sr=librosa.load(first_path,sr=44100,mono=True)
        y2,_=librosa.load(second_path,sr=sr,mono=True)
        f1=AudioCompatibility.analyze(first_path); f2=AudioCompatibility.analyze(second_path)
        if tempo_match and f1.bpm>0 and f2.bpm>0:
            target_ratio=f1.bpm/f2.bpm
            while target_ratio>1.35: target_ratio/=2
            while target_ratio<.75: target_ratio*=2
            if .75<=target_ratio<=1.35:
                y2=librosa.effects.time_stretch(y2,rate=1.0/target_ratio)
        if key_lock:
            delta=f1.key_index-f2.key_index
            if delta>6: delta-=12
            if delta<-6: delta+=12
            y2=librosa.effects.pitch_shift(y2,sr=sr,n_steps=delta)
        n=max(1,int(crossfade_seconds*sr)); n=min(n,len(y1),len(y2))
        fade_out=np.cos(np.linspace(0,np.pi/2,n))**2
        fade_in=np.sin(np.linspace(0,np.pi/2,n))**2
        mix=y1[-n:]*fade_out+y2[:n]*fade_in
        out=np.concatenate([y1[:-n],mix,y2[n:]])
        out/=max(1.0,float(np.max(np.abs(out))))
        sf.write(output_path,out,sr)
        return output_path

    @staticmethod
    def rank_candidates(reference_path,candidate_paths):
        ref=AudioCompatibility.analyze(reference_path)
        ranked=[]
        for path in candidate_paths:
            feat=AudioCompatibility.analyze(path)
            ranked.append((AudioCompatibility.score(ref,feat),path,feat))
        return sorted(ranked,reverse=True,key=lambda x:x[0])
