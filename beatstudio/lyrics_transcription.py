"""Optional local Whisper transcription with true timestamped word cues.

No cloud upload occurs. This is a CPU/GPU worker feature and is not required
for ordinary manual lyrics or LRC/SRT import.
"""
from __future__ import annotations
from dataclasses import dataclass
from .lyrics import LyricCue

def words_to_cues(segments, *, max_words=7, max_duration=4.0):
    words=[]
    for segment in segments:
        for word in segment.get("words",[]):
            label=str(word.get("word","")).strip()
            start=float(word.get("start",0));end=float(word.get("end",0))
            if label and 0<=start<end<=36000:
                words.append((label,start,end))
    words.sort(key=lambda v:v[1])
    groups=[];current=[]
    for word in words:
        if current and (len(current)>=max_words or word[2]-current[0][1]>max_duration or word[1]-current[-1][2]>.8):
            groups.append(current);current=[]
        current.append(word)
    if current:groups.append(current)
    return [LyricCue(" ".join(w[0] for w in group),group[0][1],group[-1][2],
                     words=tuple(group)).validate() for group in groups]

def transcribe_local(audio_path, *, model_size="small", device="cpu", language=None):
    if model_size not in {"tiny","base","small","medium"}:raise ValueError("Unsupported Whisper model size")
    if device not in {"cpu","cuda"}:raise ValueError("Unsupported device")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install faster-whisper on a transcription worker") from exc
    model=WhisperModel(model_size,device=device,compute_type="int8" if device=="cpu" else "float16")
    segments,meta=model.transcribe(str(audio_path),language=language,word_timestamps=True,vad_filter=True)
    result=[{"words":[{"word":w.word,"start":w.start,"end":w.end} for w in (s.words or [])]} for s in segments]
    return {"language":meta.language,"cues":[c.manifest() for c in words_to_cues(result)]}
