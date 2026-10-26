"""Optional, beat-aware video overlays. No model is loaded unless enabled."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

NEON_PALETTE = ((255, 255, 20), (255, 40, 240), (255, 220, 60), (120, 255, 255))  # BGR

@dataclass
class OverlayCue:
    start: float
    end: float
    text: str = ""
    asset: str = ""
    mode: str = "caption"  # caption, meme, asset, explainer
    trigger: str = "energy"  # energy, bass, beat, drop, onset
    threshold: float = 0.0
    def __post_init__(self):
        if self.start < 0 or self.end <= self.start:
            raise ValueError("Cue end must be after nonnegative start")
        if self.mode not in ("caption", "meme", "asset", "explainer"):
            raise ValueError("Invalid cue mode")
        if self.trigger not in ("energy", "bass", "beat", "drop", "onset"):
            raise ValueError("Invalid trigger")

@dataclass
class VisualSuiteConfig:
    body_outline: bool = False
    outline_intensity: float = 0.75
    outline_model: str = "yolo11n-seg.pt"
    outline_every: int = 2
    cues: list[OverlayCue] = field(default_factory=list)

def neon_outline(frame: np.ndarray, mask: np.ndarray, strength: float, pulse: float, color=(255, 40, 240)) -> np.ndarray:
    """Render glows around a person-instance mask, not generic frame edges."""
    if frame.shape[:2] != mask.shape[:2]:
        raise ValueError("Mask size must match frame")
    strength = float(np.clip(strength, 0, 1))
    if strength == 0:
        return frame
    binary = (mask > 127).astype(np.uint8) * 255
    contour = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, np.ones((5,5),np.uint8))
    glow = np.zeros_like(frame)
    glow[contour > 0] = color
    blur = cv2.GaussianBlur(glow, (0,0), 8)
    out = cv2.addWeighted(frame, 1, blur, min(1.0, strength * (0.3 + 0.7 * pulse)), 0)
    return cv2.addWeighted(out, 1, glow, min(1.0, strength * 0.9), 0)

class PersonSegmenter:
    """Lazy YOLO instance segmentation; no bounding-box pretend masks."""
    def __init__(self, model_name: str = "yolo11n-seg.pt", detect_every: int = 2):
        if detect_every < 1:
            raise ValueError("detect_every must be >= 1")
        self.model_name, self.detect_every = model_name, detect_every
        self.model = None
        self.cached_mask = None
        self.cached_shape = None

    def mask(self, frame: np.ndarray, index: int) -> np.ndarray:
        shape = frame.shape[:2]
        if self.cached_mask is not None and self.cached_shape == shape and index % self.detect_every:
            return self.cached_mask
        if self.model is None:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
        results = self.model.predict(frame, verbose=False)
        mask = np.zeros(shape, dtype=np.uint8)
        for result in results:
            if result.masks is None or result.boxes is None:
                continue
            for cls, m in zip(result.boxes.cls.cpu().numpy(), result.masks.data.cpu().numpy()):
                if int(cls) == 0:
                    resized = cv2.resize(m, (shape[1],shape[0]), interpolation=cv2.INTER_LINEAR)
                    mask[resized >= .5] = 255
        self.cached_mask, self.cached_shape = mask, shape
        return mask

class VisualSuite:
    def __init__(self, config: VisualSuiteConfig):
        self.config = config
        self.segmenter: Optional[PersonSegmenter] = None
        if config.body_outline:
            self.segmenter = PersonSegmenter(config.outline_model, config.outline_every)
        self._assets = {}

    def _asset(self, path: str):
        if path not in self._assets:
            p = Path(path)
            if not p.is_file() or p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                raise ValueError("Overlay asset must be a local PNG/JPG/WebP image")
            img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError("Invalid overlay image")
            self._assets[path] = img
        return self._assets[path]

    def apply(self, frame: np.ndarray, state, frame_idx: int) -> np.ndarray:
        out = frame.copy()
        if self.segmenter:
            mask = self.segmenter.mask(frame, frame_idx)
            pulse = max(float(getattr(state, "bass", 0)), float(getattr(state, "beat", 0)))
            color = NEON_PALETTE[int(getattr(state, "section", 0)) % len(NEON_PALETTE)]
            out = neon_outline(out, mask, self.config.outline_intensity, pulse, color)
        t = float(state.t)
        for cue in self.config.cues:
            if not cue.start <= t < cue.end or float(getattr(state, cue.trigger, 0)) < cue.threshold:
                continue
            intensity = float(np.clip(getattr(state, cue.trigger, 0), 0, 1))
            if cue.asset:
                out = composite_asset(out, self._asset(cue.asset), opacity=0.55+0.45*intensity)
            if cue.text:
                out = draw_caption(out, cue.text, int(getattr(state,"section",0)), intensity, cue.mode)
        return out

def composite_asset(frame: np.ndarray, asset: np.ndarray, opacity=1.0) -> np.ndarray:
    """Aspect-preserving overlay near bottom right; obey alpha where present."""
    h,w=frame.shape[:2]
    ah,aw=asset.shape[:2]
    if ah==0 or aw==0:
        return frame
    factor=min(w*0.40/aw,h*0.40/ah,1.0)
    sw,sh=max(1,int(aw*factor)),max(1,int(ah*factor))
    resized=cv2.resize(asset,(sw,sh),interpolation=cv2.INTER_AREA)
    x,y=w-sw-max(4,w//30),h-sh-max(4,h//25)
    if x<0 or y<0:
        return frame
    out=frame.copy()
    roi=out[y:y+sh,x:x+sw].astype(np.float32)
    alpha=(resized[:,:,3:4].astype(np.float32)/255.0 if resized.shape[2]==4 else np.ones((sh,sw,1),np.float32))*float(np.clip(opacity,0,1))
    out[y:y+sh,x:x+sw]=np.clip(roi*(1-alpha)+resized[:,:,:3].astype(np.float32)*alpha,0,255).astype(np.uint8)
    return out

def draw_caption(frame: np.ndarray, text: str, section: int, intensity: float, mode: str) -> np.ndarray:
    """Simple legible typography; AI storytelling produces the cue data separately."""
    out=frame.copy()
    h,w=out.shape[:2]
    color=NEON_PALETTE[section % len(NEON_PALETTE)]
    lines=[text[i:i+48] for i in range(0,min(len(text),144),48)] or [""]
    scale=max(.45,min(1.2,w/1000))*(1+.1*float(np.clip(intensity,0,1)))
    for i,line in enumerate(lines):
        y=max(25,h-int(h*.12)-int((len(lines)-1-i)*scale*44))
        x=max(10,int(w*.06))
        cv2.putText(out,line,(x+2,y+2),cv2.FONT_HERSHEY_SIMPLEX,scale,(0,0,0),4,cv2.LINE_AA)
        cv2.putText(out,line,(x,y),cv2.FONT_HERSHEY_SIMPLEX,scale,color,2,cv2.LINE_AA)
    return out
