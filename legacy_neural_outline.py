"""
Beat-Sync VFX Pipeline — Neural Body Outline Edition

Primary body outline:
  Ultralytics YOLO segmentation (person class) -> pixel mask -> optical-flow temporal
  stabilization -> morphology -> smoothed neon contour.

Fallback:
  OpenCV HOG person detector + GrabCut, so the script remains usable if
  `ultralytics` or segmentation weights are unavailable.

Audio:
  Librosa beat/onset detection. FFmpeg is used to mux the processed video with audio.

Install:
  pip install ultralytics opencv-python librosa numpy soundfile

FFmpeg must also be available on PATH.
"""

from __future__ import annotations

import math
import os
import random
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import librosa
import numpy as np


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

VIDEO_PATH = "/content/Screen Recording 2026-05-19 070147 - Trim.mp4"
AUDIO_PATH = "/content/black-box-ficx-your-heart-129460.mp3"
OUTPUT_PATH = "output_video_neural_outline.mp4"

# Any Ultralytics segmentation checkpoint can be used here.
# yolo11n-seg.pt is small and fast; a larger *-seg model improves silhouettes.
SEGMENTATION_MODEL = "yolo11n-seg.pt"
SEG_CONF = 0.35
SEG_IOU = 0.60
SEG_IMGSZ = 640
PERSON_CLASS_ID = 0

# Run neural segmentation every N frames and propagate mask between detections.
# 1 = maximum accuracy, 2-3 = faster.
SEGMENT_EVERY = 2

# Temporal mask smoothing. Higher = follow current frame faster; lower = smoother.
MASK_EMA_ALPHA = 0.72
USE_OPTICAL_FLOW = True

# Reject tiny person masks.
MIN_PERSON_AREA_RATIO = 0.003

# Outline styling
OUTLINE_COLOR: Tuple[int, int, int] = (255, 80, 255)  # BGR
OUTLINE_THICKNESS = 2
OUTLINE_GLOW_SIGMA = 10.0
OUTLINE_GLOW_STRENGTH = 0.85
OUTLINE_CORE_STRENGTH = 1.0
CONTOUR_EPSILON_RATIO = 0.0015

# Beat effects
BEAT_WINDOW = 0.070
ONSET_WINDOW = 0.050

# Particles
MAX_PARTICLES = 500

# Optional preview (desktop only)
PREVIEW = False

GLOW_COLORS: List[Tuple[int, int, int]] = [
    (255, 60, 60),
    (60, 255, 60),
    (60, 60, 255),
    (255, 220, 40),
    (40, 230, 255),
    (220, 40, 255),
    (255, 140, 30),
    (160, 40, 255),
]


# -----------------------------------------------------------------------------
# SMALL HELPERS
# -----------------------------------------------------------------------------

def _nearest_distance(t: float, events: np.ndarray) -> float:
    if events.size == 0:
        return float("inf")
    idx = int(np.searchsorted(events, t))
    d = []
    if idx < len(events):
        d.append(abs(float(events[idx]) - t))
    if idx > 0:
        d.append(abs(float(events[idx - 1]) - t))
    return min(d) if d else float("inf")


def _pulse(t: float, events: np.ndarray, window: float) -> float:
    d = _nearest_distance(t, events)
    if d >= window:
        return 0.0
    x = d / window
    return float(0.5 * (1.0 + math.cos(math.pi * x)))


def _ensure_uint8_mask(mask: np.ndarray) -> np.ndarray:
    if mask.dtype != np.uint8:
        mask = np.clip(mask, 0, 255).astype(np.uint8)
    return mask


# -----------------------------------------------------------------------------
# AUDIO / BEAT ANALYSIS
# -----------------------------------------------------------------------------

class BeatDetector:
    def __init__(self, audio_path: str):
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        self.duration = float(librosa.get_duration(y=y, sr=sr))

        _, percussive = librosa.effects.hpss(y)
        onset_env = librosa.onset.onset_strength(
            y=percussive, sr=sr, aggregate=np.median
        )

        self.onsets = np.asarray(
            librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=sr,
                backtrack=False,
                units="time",
            ),
            dtype=np.float32,
        )

        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env, sr=sr
        )
        self.beats = np.asarray(
            librosa.frames_to_time(beat_frames, sr=sr), dtype=np.float32
        )
        self.tempo = float(np.asarray(tempo).reshape(-1)[0])

        print(
            f"[BeatDetector] duration={self.duration:.2f}s | "
            f"tempo={self.tempo:.1f} BPM | beats={len(self.beats)} | "
            f"onsets={len(self.onsets)}"
        )

    def beat_strength(self, t: float) -> float:
        return _pulse(t, self.beats, BEAT_WINDOW)

    def onset_strength(self, t: float) -> float:
        return _pulse(t, self.onsets, ONSET_WINDOW)


# -----------------------------------------------------------------------------
# BODY SEGMENTATION
# -----------------------------------------------------------------------------

class NeuralBodySegmenter:
    """
    Accurate person silhouettes using instance segmentation.

    Pipeline:
      1. YOLO segmentation masks for class `person`.
      2. Union of all valid person instances.
      3. On skipped frames, warp previous mask with dense optical flow.
      4. EMA blend previous/current masks to suppress flicker.
      5. Morphological cleanup and component filtering.

    If the neural model cannot be loaded, the class falls back to HOG + GrabCut.
    """

    def __init__(self, model_path: str = SEGMENTATION_MODEL):
        self.model_path = model_path
        self.model = None
        self.backend = "fallback"
        self.frame_index = 0
        self.prev_gray: Optional[np.ndarray] = None
        self.prev_mask_f: Optional[np.ndarray] = None
        self.last_detection_mask: Optional[np.ndarray] = None

        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        try:
            from ultralytics import YOLO  # type: ignore

            self.model = YOLO(model_path)
            self.backend = "yolo-seg"
            print(f"[BodySegmenter] backend=YOLO segmentation | model={model_path}")
        except Exception as exc:
            print(
                "[BodySegmenter] YOLO segmentation unavailable; "
                f"using HOG+GrabCut fallback. Reason: {exc}"
            )

    def _segment_yolo(self, frame: np.ndarray) -> np.ndarray:
        assert self.model is not None
        h, w = frame.shape[:2]
        combined = np.zeros((h, w), dtype=np.uint8)

        results = self.model.predict(
            source=frame,
            conf=SEG_CONF,
            iou=SEG_IOU,
            imgsz=SEG_IMGSZ,
            classes=[PERSON_CLASS_ID],
            verbose=False,
        )

        if not results:
            return combined

        result = results[0]
        if result.masks is None or result.boxes is None:
            return combined

        masks = result.masks.data.detach().cpu().numpy()
        classes = result.boxes.cls.detach().cpu().numpy().astype(int)

        min_area = int(h * w * MIN_PERSON_AREA_RATIO)

        for mask, cls_id in zip(masks, classes):
            if cls_id != PERSON_CLASS_ID:
                continue
            resized = cv2.resize(mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
            binary = (resized >= 0.5).astype(np.uint8) * 255
            if cv2.countNonZero(binary) < min_area:
                continue
            combined = cv2.bitwise_or(combined, binary)

        return combined

    def _segment_fallback(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        combined = np.zeros((h, w), dtype=np.uint8)

        # Downscale HOG input for speed while preserving output coordinates.
        scale = min(1.0, 720.0 / max(h, w))
        small = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1.0 else frame
        rects, weights = self.hog.detectMultiScale(
            small, winStride=(8, 8), padding=(8, 8), scale=1.05
        )

        inv = 1.0 / scale
        for rect, weight in zip(rects, weights):
            if float(weight) < 0.25:
                continue
            x, y, bw, bh = [int(v * inv) for v in rect]
            x = max(1, min(x, w - 2))
            y = max(1, min(y, h - 2))
            bw = max(2, min(bw, w - x - 1))
            bh = max(2, min(bh, h - y - 1))

            gc_mask = np.zeros((h, w), np.uint8)
            bgd = np.zeros((1, 65), np.float64)
            fgd = np.zeros((1, 65), np.float64)
            try:
                cv2.grabCut(
                    frame,
                    gc_mask,
                    (x, y, bw, bh),
                    bgd,
                    fgd,
                    iterCount=2,
                    mode=cv2.GC_INIT_WITH_RECT,
                )
                fg = np.where(
                    (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD),
                    255,
                    0,
                ).astype(np.uint8)
                combined = cv2.bitwise_or(combined, fg)
            except cv2.error:
                combined[y : y + bh, x : x + bw] = 255

        return combined

    @staticmethod
    def _warp_mask_with_flow(
        prev_gray: np.ndarray,
        gray: np.ndarray,
        prev_mask: np.ndarray,
    ) -> np.ndarray:
        """Warp previous segmentation into the current frame using dense optical flow."""
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray,
            gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=21,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )

        h, w = gray.shape
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = (grid_x - flow[..., 0]).astype(np.float32)
        map_y = (grid_y - flow[..., 1]).astype(np.float32)
        warped = cv2.remap(
            prev_mask.astype(np.float32),
            map_x,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        return warped

    @staticmethod
    def _cleanup(mask: np.ndarray) -> np.ndarray:
        mask = _ensure_uint8_mask(mask)

        # Soft masks are thresholded after temporal blending.
        _, mask = cv2.threshold(mask, 112, 255, cv2.THRESH_BINARY)

        close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k, iterations=1)

        # Remove tiny disconnected components while preserving multiple people.
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if n <= 1:
            return mask

        h, w = mask.shape
        min_area = max(150, int(h * w * MIN_PERSON_AREA_RATIO * 0.35))
        cleaned = np.zeros_like(mask)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                cleaned[labels == i] = 255
        return cleaned

    def segment(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        run_detector = (
            self.last_detection_mask is None
            or self.frame_index % max(1, SEGMENT_EVERY) == 0
        )

        current_mask: Optional[np.ndarray] = None
        if run_detector:
            if self.backend == "yolo-seg":
                try:
                    current_mask = self._segment_yolo(frame)
                except Exception as exc:
                    print(f"[BodySegmenter] YOLO inference failed once; fallback: {exc}")
                    current_mask = self._segment_fallback(frame)
            else:
                current_mask = self._segment_fallback(frame)
            self.last_detection_mask = current_mask.copy()

        # Propagate previous mask between neural detections.
        propagated: Optional[np.ndarray] = None
        if (
            USE_OPTICAL_FLOW
            and self.prev_gray is not None
            and self.prev_mask_f is not None
            and self.prev_gray.shape == gray.shape
        ):
            propagated = self._warp_mask_with_flow(
                self.prev_gray,
                gray,
                self.prev_mask_f,
            )

        if current_mask is None:
            if propagated is not None:
                mask_f = propagated
            elif self.prev_mask_f is not None:
                mask_f = self.prev_mask_f.copy()
            elif self.last_detection_mask is not None:
                mask_f = self.last_detection_mask.astype(np.float32)
            else:
                mask_f = np.zeros(gray.shape, dtype=np.float32)
        else:
            curr_f = current_mask.astype(np.float32)
            if propagated is not None:
                # Detector result dominates; propagated mask suppresses flicker.
                mask_f = (
                    MASK_EMA_ALPHA * curr_f
                    + (1.0 - MASK_EMA_ALPHA) * propagated
                )
            elif self.prev_mask_f is not None:
                mask_f = (
                    MASK_EMA_ALPHA * curr_f
                    + (1.0 - MASK_EMA_ALPHA) * self.prev_mask_f
                )
            else:
                mask_f = curr_f

        cleaned = self._cleanup(mask_f)

        self.prev_gray = gray
        self.prev_mask_f = cleaned.astype(np.float32)
        self.frame_index += 1
        return cleaned

    @staticmethod
    def draw_outline(
        frame: np.ndarray,
        mask: np.ndarray,
        color: Tuple[int, int, int] = OUTLINE_COLOR,
        intensity: float = 1.0,
    ) -> np.ndarray:
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )
        if not contours:
            return frame

        out = frame.copy()
        core = np.zeros_like(frame)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:
                continue

            perimeter = cv2.arcLength(contour, True)
            eps = max(0.5, CONTOUR_EPSILON_RATIO * perimeter)
            smooth = cv2.approxPolyDP(contour, eps, True)
            cv2.drawContours(
                core,
                [smooth],
                -1,
                color,
                OUTLINE_THICKNESS,
                cv2.LINE_AA,
            )

        # Multiple Gaussian scales make a natural halo without thick ugly bands.
        glow1 = cv2.GaussianBlur(core, (0, 0), OUTLINE_GLOW_SIGMA)
        glow2 = cv2.GaussianBlur(core, (0, 0), OUTLINE_GLOW_SIGMA * 2.2)

        out = cv2.addWeighted(
            out, 1.0, glow2, 0.30 * OUTLINE_GLOW_STRENGTH * intensity, 0
        )
        out = cv2.addWeighted(
            out, 1.0, glow1, 0.62 * OUTLINE_GLOW_STRENGTH * intensity, 0
        )
        out = cv2.addWeighted(
            out, 1.0, core, OUTLINE_CORE_STRENGTH * intensity, 0
        )
        return out


# -----------------------------------------------------------------------------
# PARTICLES
# -----------------------------------------------------------------------------

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    lifetime: int
    max_lifetime: int
    size: float
    trail: List[Tuple[int, int]] = field(default_factory=list)

    def update(self) -> bool:
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.vy += 0.08
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        return max(0.0, self.lifetime / max(1, self.max_lifetime))


class ParticleSystem:
    def __init__(self, max_particles: int = MAX_PARTICLES):
        self.max_particles = max_particles
        self.pool: List[Particle] = []

    def emit(self, shape: Tuple[int, ...], n: int, strength: float):
        h, w = shape[:2]
        room = max(0, self.max_particles - len(self.pool))
        for _ in range(min(n, room)):
            life = random.randint(16, 38)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.0, 5.5) * max(0.2, strength)
            self.pool.append(
                Particle(
                    x=random.uniform(0, w - 1),
                    y=random.uniform(0, h - 1),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=random.choice(GLOW_COLORS),
                    lifetime=life,
                    max_lifetime=life,
                    size=random.uniform(1.0, 4.5),
                )
            )

    def step(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        overlay = np.zeros_like(frame, dtype=np.float32)
        alive: List[Particle] = []

        for p in self.pool:
            if not p.update():
                continue
            if not (0 <= p.x < w and 0 <= p.y < h):
                continue
            alive.append(p)

            if len(p.trail) > 1:
                for i in range(1, len(p.trail)):
                    a = p.alpha * (i / len(p.trail)) * 0.32
                    cv2.line(
                        overlay,
                        p.trail[i - 1],
                        p.trail[i],
                        tuple(float(c) * a for c in p.color),
                        1,
                        cv2.LINE_AA,
                    )

            cv2.circle(
                overlay,
                (int(p.x), int(p.y)),
                max(1, int(p.size * p.alpha)),
                tuple(float(c) * p.alpha for c in p.color),
                -1,
                cv2.LINE_AA,
            )

        self.pool = alive
        glow = cv2.GaussianBlur(overlay, (0, 0), 5)
        return np.clip(frame.astype(np.float32) + glow, 0, 255).astype(np.uint8)


# -----------------------------------------------------------------------------
# EFFECTS
# -----------------------------------------------------------------------------

class Effects:
    @staticmethod
    def zoom(frame: np.ndarray, strength: float) -> np.ndarray:
        if strength <= 0.01:
            return frame
        h, w = frame.shape[:2]
        scale = 1.0 + 0.055 * strength
        nw, nh = max(2, int(w / scale)), max(2, int(h / scale))
        x, y = (w - nw) // 2, (h - nh) // 2
        crop = frame[y : y + nh, x : x + nw]
        return cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def shake(frame: np.ndarray, strength: float) -> np.ndarray:
        if strength < 0.18:
            return frame
        h, w = frame.shape[:2]
        m = max(1, int(7 * strength))
        dx, dy = random.randint(-m, m), random.randint(-m, m)
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(
            frame, M, (w, h), borderMode=cv2.BORDER_REFLECT
        )

    @staticmethod
    def chromatic(frame: np.ndarray, strength: float) -> np.ndarray:
        if strength < 0.2:
            return frame
        h, w = frame.shape[:2]
        shift = max(1, int(7 * strength))
        b, g, r = cv2.split(frame)
        mr = np.float32([[1, 0, shift], [0, 1, 0]])
        mb = np.float32([[1, 0, -shift], [0, 1, 0]])
        r = cv2.warpAffine(r, mr, (w, h), borderMode=cv2.BORDER_REFLECT)
        b = cv2.warpAffine(b, mb, (w, h), borderMode=cv2.BORDER_REFLECT)
        return cv2.merge((b, g, r))

    @staticmethod
    def flash(frame: np.ndarray, strength: float) -> np.ndarray:
        if strength < 0.35:
            return frame
        white = np.full_like(frame, 255)
        alpha = 0.10 * strength
        return cv2.addWeighted(frame, 1 - alpha, white, alpha, 0)

    @staticmethod
    def bloom(frame: np.ndarray, intensity: float = 0.22) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 205, 255, cv2.THRESH_BINARY)
        bright = cv2.bitwise_and(frame, frame, mask=bright_mask)
        glow = cv2.GaussianBlur(bright, (0, 0), 16)
        return cv2.addWeighted(frame, 1.0, glow, intensity, 0)

    @staticmethod
    def grade(frame: np.ndarray) -> np.ndarray:
        f = frame.astype(np.float32)
        b, g, r = cv2.split(f)
        lum = 0.114 * b + 0.587 * g + 0.299 * r
        dark = np.clip(1 - lum / 255.0, 0, 1)
        light = np.clip(lum / 255.0, 0, 1)
        b = np.clip(b + 10 * dark - 6 * light, 0, 255)
        g = np.clip(g + 5 * dark, 0, 255)
        r = np.clip(r + 12 * light, 0, 255)
        return cv2.merge((b, g, r)).astype(np.uint8)

    @staticmethod
    def vignette(frame: np.ndarray, strength: float = 0.18) -> np.ndarray:
        h, w = frame.shape[:2]
        kx = cv2.getGaussianKernel(w, max(1.0, w / 2.2))
        ky = cv2.getGaussianKernel(h, max(1.0, h / 2.2))
        mask = ky @ kx.T
        mask /= max(mask.max(), 1e-6)
        mask = (1.0 - strength) + strength * mask
        return np.clip(frame.astype(np.float32) * mask[..., None], 0, 255).astype(np.uint8)


# -----------------------------------------------------------------------------
# VIDEO PROCESSOR
# -----------------------------------------------------------------------------

class VideoProcessor:
    def __init__(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        preview: bool = PREVIEW,
    ):
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self.preview = preview

        if shutil.which("ffmpeg") is None:
            raise RuntimeError("FFmpeg is required but was not found on PATH.")
        if not os.path.exists(video_path):
            raise FileNotFoundError(video_path)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)

        self.beats = BeatDetector(audio_path)
        self.body = NeuralBodySegmenter()
        self.particles = ParticleSystem()
        self.fx = Effects()

    def _process_frame(self, frame: np.ndarray, t: float) -> np.ndarray:
        beat = self.beats.beat_strength(t)
        onset = self.beats.onset_strength(t)
        impact = max(beat, onset)

        mask = self.body.segment(frame)

        # Outline is intentionally less intense between beats, but remains visible.
        outline_strength = 0.55 + 0.45 * impact
        frame = self.body.draw_outline(
            frame,
            mask,
            color=OUTLINE_COLOR,
            intensity=outline_strength,
        )

        if impact > 0.22:
            self.particles.emit(frame.shape, n=int(12 + 55 * impact), strength=impact)
        frame = self.particles.step(frame)

        frame = self.fx.zoom(frame, beat)
        frame = self.fx.chromatic(frame, onset)
        frame = self.fx.shake(frame, onset)
        frame = self.fx.flash(frame, max(beat, onset))

        frame = self.fx.bloom(frame)
        frame = self.fx.grade(frame)
        frame = self.fx.vignette(frame)
        return frame

    def run(self) -> None:
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open {self.video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        temp_video = str(Path(self.output_path).with_suffix(".video_only.mp4"))
        writer = cv2.VideoWriter(
            temp_video,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Could not create temporary video writer.")

        frame_n = 0
        started = time.time()
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                t = frame_n / fps
                if t > self.beats.duration:
                    break

                out = self._process_frame(frame, t)
                if out.shape[:2] != (height, width):
                    out = cv2.resize(out, (width, height))
                writer.write(out)

                frame_n += 1
                if frame_n % max(1, int(fps * 5)) == 0:
                    elapsed = max(time.time() - started, 1e-6)
                    pct = 100 * frame_n / max(total, 1)
                    print(
                        f"[Render] frame={frame_n}/{total} ({pct:.1f}%) | "
                        f"effective={frame_n / elapsed:.2f} fps"
                    )

                if self.preview:
                    cv2.imshow("Neural Outline VFX", out)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            cap.release()
            writer.release()
            if self.preview:
                cv2.destroyAllWindows()

        print("[Mux] Adding audio with FFmpeg...")
        command = [
            "ffmpeg",
            "-y",
            "-i",
            temp_video,
            "-i",
            self.audio_path,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-movflags",
            "+faststart",
            self.output_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("FFmpeg mux failed:\n" + result.stderr[-3000:])

        try:
            os.remove(temp_video)
        except OSError:
            pass

        print(f"[Done] Saved: {self.output_path}")


if __name__ == "__main__":
    VideoProcessor(
        video_path=VIDEO_PATH,
        audio_path=AUDIO_PATH,
        output_path=OUTPUT_PATH,
        preview=PREVIEW,
    ).run()