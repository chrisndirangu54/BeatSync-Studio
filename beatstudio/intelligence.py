from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import librosa

@dataclass
class BeatState:
    t: float
    beat: float = 0.0
    onset: float = 0.0
    bass: float = 0.0
    mids: float = 0.0
    treble: float = 0.0
    energy: float = 0.0
    brightness: float = 0.0
    drop: float = 0.0
    section: int = 0

class IntelligentBeatSync:
    """Precomputes musical features and exposes smooth per-time control signals."""
    def __init__(self, audio_path: str, level: int = 2):
        self.audio_path = audio_path
        self.level = level
        self.y, self.sr = librosa.load(audio_path, sr=44100, mono=True)
        self.duration = librosa.get_duration(y=self.y, sr=self.sr)
        self.hop = 512
        self.times = librosa.frames_to_time(np.arange(1 + len(self.y)//self.hop), sr=self.sr, hop_length=self.hop)
        self._analyse()

    @staticmethod
    def _norm(x):
        x = np.asarray(x, dtype=np.float32)
        if x.size == 0: return x
        lo, hi = np.percentile(x, 5), np.percentile(x, 95)
        if hi <= lo: return np.zeros_like(x)
        return np.clip((x-lo)/(hi-lo), 0, 1)

    def _analyse(self):
        y, sr, hop = self.y, self.sr, self.hop
        S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        self.rms = self._norm(librosa.feature.rms(S=S)[0])
        self.centroid = self._norm(librosa.feature.spectral_centroid(S=S, sr=sr)[0])
        def band(lo, hi):
            idx = (freqs >= lo) & (freqs < hi)
            return self._norm(S[idx].mean(axis=0) if np.any(idx) else np.zeros(S.shape[1]))
        self.bass = band(20, 180)
        self.mids = band(180, 2500)
        self.treble = band(2500, 12000)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
        self.onset_env = self._norm(onset_env)
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=hop)
        self.tempo = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
        self.beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
        self.onset_times = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop, units='time')
        delta = np.maximum(0, np.gradient(self.rms))
        self.drop_curve = self._norm(0.55*delta + 0.45*self.bass[:len(delta)])
        self.section_boundaries = np.array([0.0, self.duration])
        if self.level >= 3 and self.duration > 8:
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=8, hop_length=hop)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop)
            X = np.vstack([librosa.util.normalize(mfcc, axis=1), librosa.util.normalize(chroma, axis=1)])
            n_segments = max(2, min(10, int(round(self.duration / 20.0))))
            try:
                bounds = librosa.segment.agglomerative(X, k=n_segments)
                secs = librosa.frames_to_time(bounds, sr=sr, hop_length=hop)
                self.section_boundaries = np.unique(np.r_[0.0, secs, self.duration])
            except Exception:
                pass

    def _sample(self, arr, t):
        if len(arr) == 0: return 0.0
        idx = int(np.clip(round(t * self.sr / self.hop), 0, len(arr)-1))
        return float(arr[idx])

    @staticmethod
    def _pulse(t, events, width):
        if len(events) == 0: return 0.0
        i = np.searchsorted(events, t)
        d = min(abs(events[min(i, len(events)-1)]-t), abs(events[max(0, i-1)]-t))
        return float(max(0.0, 1.0-d/width)) if d < width else 0.0

    def state(self, t: float) -> BeatState:
        sec = max(0, int(np.searchsorted(self.section_boundaries, t, side='right')-1))
        return BeatState(
            t=t,
            beat=self._pulse(t, self.beat_times, 0.09),
            onset=self._pulse(t, self.onset_times, 0.07),
            bass=self._sample(self.bass, t),
            mids=self._sample(self.mids, t),
            treble=self._sample(self.treble, t),
            energy=self._sample(self.rms, t),
            brightness=self._sample(self.centroid, t),
            drop=self._sample(self.drop_curve, t),
            section=sec,
        )
