"""Timed lyrics, LRC/SRT parsing, customisable neon typography."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re

STYLES={"karaoke","calligraphy","brush","neon_script","serif","bold_pop","gothic","minimal"}
SIGNALS={"beat","onset","bass","mids","treble","energy","drop"}
FONTS={"sans","serif","script","handwriting","display","mono"}
COLOR=re.compile(r"^#[0-9a-fA-F]{6}$")
STAMP=re.compile(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]")
SRTSTAMP=re.compile(r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})")
@dataclass(frozen=True)
class LyricCue:
    text:str
    start:float
    end:float
    style:str="karaoke"
    font:str="sans"
    color:str="#FFFFFF"
    highlight:str="#FF40FF"
    outline:str="#101020"
    position:str="bottom"
    signal:str="beat"
    glow:bool=True
    bounce:bool=True
    words:tuple=()
    def validate(self):
        if not isinstance(self.text,str) or not 1<=len(self.text)<=240:raise ValueError("Invalid lyric")
        if not 0<=self.start<self.end<=36000:raise ValueError("Invalid lyric time")
        if self.style not in STYLES or self.font not in FONTS or self.signal not in SIGNALS:raise ValueError("Invalid style/font/signal")
        if self.position not in {"top","middle","bottom"}:raise ValueError("Invalid lyric placement")
        if not all(COLOR.fullmatch(v) for v in (self.color,self.highlight,self.outline)):raise ValueError("Invalid hex colors")
        for word in self.words:
            if len(word)!=3 or not isinstance(word[0],str) or not self.start<=float(word[1])<float(word[2])<=self.end:
                raise ValueError("Invalid word timestamps")
        return self
    def manifest(self):return asdict(self.validate())

def parse_lrc(text):
    starts=[]
    for line in text.splitlines():
        hits=list(STAMP.finditer(line))
        lyric=STAMP.sub("",line).strip()
        if not lyric:continue
        for match in hits:
            fraction=match.group(3) or "0"
            t=int(match.group(1))*60+int(match.group(2))+int(fraction)/10**len(fraction)
            starts.append((t,lyric))
    starts.sort()
    return [LyricCue(lyric,t,starts[i+1][0] if i+1<len(starts) and starts[i+1][0]>t else t+3).validate()
            for i,(t,lyric) in enumerate(starts)]

def parse_srt(text):
    cues=[]
    for block in re.split(r"\n\s*\n",text.replace("\r\n","\n").strip()):
        lines=block.splitlines()
        line=next((i for i,v in enumerate(lines) if "-->" in v),None)
        if line is None:continue
        stamps=SRTSTAMP.findall(lines[line])
        if len(stamps)!=2:continue
        def seconds(parts):
            h,m,s,ms=map(int,parts)
            return 3600*h+60*m+s+ms/1000
        lyric=" ".join(lines[line+1:]).strip()
        if lyric:cues.append(LyricCue(lyric,seconds(stamps[0]),seconds(stamps[1])).validate())
    return sorted(cues,key=lambda x:x.start)

def parse_lyrics(text,extension):
    if extension.lower()==".lrc":return parse_lrc(text)
    if extension.lower()==".srt":return parse_srt(text)
    raise ValueError("Supported lyrics: .lrc, .srt")
