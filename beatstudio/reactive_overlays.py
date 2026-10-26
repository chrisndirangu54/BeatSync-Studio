"""Optional beat-reactive overlays for BeatSync Studio.

YOLO is lazy-loaded and never downloaded unless neural_outline is enabled.
Media overlays accept local project files only; no untrusted remote URL fetching.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

NEON_BGR = {"cyan": (255, 255, 0), "magenta": (255, 60, 255), "blue": (255, 110, 30), "lime": (120, 255, 90)}

@dataclass
class OverlayConfig:
    neural_outline: bool = False
    outline_color: str = "magenta"
    outline_intensity: float = 0.8
    model_path: str = "yolo11n-seg.pt"
    # Static media layers can contain transparent PNG, GIF, or short video.
    media_paths: list[str] = field(default_factory=list)
    media_opacity: float = 0.7
    caption: str = ""
    # Music event that controls layer visibility/intensity.
    trigger: str = "beat"

class NeuralOutline:
    def __init__(self, model_path: str):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install requirements-vision.txt to enable YOLO outlines") from exc
        self.model = YOLO(model_path)

    def apply(self, frame: np.ndarray, color: tuple[int, int, int], strength: float) -> np.ndarray:
        result = self.model.predict(frame, classes=[0], verbose=False, conf=0.35)[0]
        if result.masks is None or result.boxes is None:
            return frame
        h, w = frame.shape[:2]
        core = np.zeros_like(frame)
        masks = result.masks.data.cpu().numpy()
        for m, cls in zip(masks, result.boxes.cls.cpu().numpy()):
            if int(cls) != 0:
                continue
            mask = (cv2.resize(m, (w, h)) > 0.5).astype(np.uint8) * 255
            if cv2.countNonZero(mask) < w*h*0.003:
                continue
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(core, contours, -1, color, 2, cv2.LINE_AA)
        glow = cv2.GaussianBlur(core, (0, 0), 10)
        return cv2.addWeighted(cv2.addWeighted(frame, 1, glow, 0.9*strength, 0), 1, core, strength, 0)

class MediaLayer:
    def __init__(self, path: str):
        p = Path(path)
        if not p.is_file():
            raise ValueError(f"Overlay media not found: {p}")
        self.path = str(p)
        self.still = None
        self.frames = None
        self.capture = None
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            self.still = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)
            if self.still is None:
                raise ValueError(f"Invalid overlay image: {p}")
        elif p.suffix.lower() == ".gif":
            from PIL import Image, ImageSequence
            with Image.open(p) as im:
                self.frames = [cv2.cvtColor(np.asarray(f.convert("RGBA")), cv2.COLOR_RGBA2BGRA)
                               for f in ImageSequence.Iterator(im)]
            if not self.frames:
                raise ValueError(f"Empty GIF: {p}")
        elif p.suffix.lower() in {".mp4", ".mov", ".webm"}:
            self.capture = cv2.VideoCapture(self.path)
            if not self.capture.isOpened():
                raise ValueError(f"Invalid overlay video: {p}")
        else:
            raise ValueError(f"Unsupported overlay media: {p.suffix}")

    def read(self, frame_index: int):
        if self.still is not None:
            return self.still
        if self.frames is not None:
            return self.frames[frame_index % len(self.frames)]
        ok, frame = self.capture.read()
        if not ok:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.capture.read()
        return frame if ok else None

    def close(self):
        if self.capture:
            self.capture.release()

def composite(frame: np.ndarray, layer: np.ndarray, opacity: float) -> np.ndarray:
    if layer is None:
        return frame
    h, w = frame.shape[:2]
    lh, lw = layer.shape[:2]
    # Fit content in a lower-right picture-in-picture region, preserve aspect ratio.
    target_w = max(1, int(w*0.31))
    target_h = max(1, int(h*0.32))
    scale = min(target_w/max(1,lw), target_h/max(1,lh))
    nw, nh = max(1, int(lw*scale)), max(1, int(lh*scale))
    layer = cv2.resize(layer, (nw, nh), interpolation=cv2.INTER_AREA)
    x, y = max(0,w-nw-int(w*0.035)), max(0,h-nh-int(h*0.07))
    roi = frame[y:y+nh, x:x+nw]
    alpha = np.full((nh,nw,1), float(np.clip(opacity,0,1)), np.float32)
    if layer.shape[2] == 4:
        alpha *= layer[:,:,3:4].astype(np.float32)/255
    rgb = layer[:,:,:3].astype(np.float32)
    roi[:] = np.clip(roi.astype(np.float32)*(1-alpha)+rgb*alpha,0,255).astype(np.uint8)
    return frame

class ReactiveOverlayEngine:
    def __init__(self, config: OverlayConfig):
        self.config = config
        if config.outline_color not in NEON_BGR:
            raise ValueError("Unknown neon color")
        if config.trigger not in {"beat","onset","bass","mids","treble","drop","energy"}:
            raise ValueError("Invalid trigger")
        self.outline = NeuralOutline(config.model_path) if config.neural_outline else None
        self.media = [MediaLayer(p) for p in config.media_paths]

    def apply(self, frame, state, index):
        signal = float(np.clip(getattr(state, self.config.trigger, 0.0),0,1))
        out = frame.copy()
        if self.outline:
            out = self.outline.apply(out, NEON_BGR[self.config.outline_color],
                                     float(np.clip(self.config.outline_intensity,0,1))*(0.3+0.7*signal))
        for layer in self.media:
            out = composite(out, layer.read(index), self.config.media_opacity*(0.2+0.8*signal))
        if self.config.caption:
            caption = self.config.caption.replace("\\n", " ")[:100]
            h,w = out.shape[:2]
            cv2.putText(out, caption, (int(w*.04), int(h*.12)),
                        cv2.FONT_HERSHEY_SIMPLEX, min(1.0,max(.4,w/1200)),
                        NEON_BGR[self.config.outline_color],2,cv2.LINE_AA)
        return out

    def close(self):
        for layer in self.media:
            layer.close()
