from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import cv2
import numpy as np

from .intelligence import IntelligentBeatSync


@dataclass
class DirectorConfig:
    fps: float = 30.0
    width: int = 1280
    height: int = 720
    min_shot_seconds: float = 0.55
    max_shot_seconds: float = 4.0
    cut_on_sections: bool = True
    cut_on_drops: bool = True
    beat_group_low_energy: int = 8
    beat_group_high_energy: int = 2


class _ClipCursor:
    def __init__(self, path: str):
        self.path = path
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open source clip: {path}")

    def frame(self, width: int, height: int):
        ok, frm = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frm = self.cap.read()
        if not ok:
            return np.zeros((height, width, 3), dtype=np.uint8)

        h, w = frm.shape[:2]
        target = width / height
        aspect = w / max(h, 1)
        if aspect > target:
            crop_w = int(h * target)
            x = max(0, (w - crop_w) // 2)
            frm = frm[:, x:x + crop_w]
        else:
            crop_h = int(w / target)
            y = max(0, (h - crop_h) // 2)
            frm = frm[y:y + crop_h, :]
        return cv2.resize(frm, (width, height), interpolation=cv2.INTER_AREA)

    def close(self):
        self.cap.release()


class MultiClipDirector:
    """
    Creates a silent edit from multiple source clips using musical structure.

    Editing policy:
    - section changes always encourage a new shot;
    - likely drops trigger cuts when enabled;
    - beat grouping becomes shorter as musical energy increases;
    - the same source is avoided on consecutive cuts when alternatives exist.

    The resulting silent edit is passed into VideoRenderer, which applies the
    chosen effect rack and muxes the selected/generated music track.
    """

    def __init__(
        self,
        clip_paths: List[str],
        audio_path: str,
        output_path: str,
        *,
        intelligence_level: int = 3,
        config: Optional[DirectorConfig] = None,
    ):
        if not clip_paths:
            raise ValueError("At least one clip is required.")
        self.clip_paths = clip_paths
        self.audio_path = audio_path
        self.output_path = output_path
        self.config = config or DirectorConfig()
        self.sync = IntelligentBeatSync(audio_path, intelligence_level)

    def _is_near(self, t: float, events: np.ndarray, tolerance: float = 0.045) -> bool:
        if len(events) == 0:
            return False
        i = np.searchsorted(events, t)
        candidates = []
        if i < len(events):
            candidates.append(abs(events[i] - t))
        if i > 0:
            candidates.append(abs(events[i - 1] - t))
        return bool(candidates and min(candidates) <= tolerance)

    def build(self, progress=None) -> str:
        cfg = self.config
        cursors = [_ClipCursor(p) for p in self.clip_paths]
        writer = cv2.VideoWriter(
            self.output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            cfg.fps,
            (cfg.width, cfg.height),
        )
        if not writer.isOpened():
            for cursor in cursors:
                cursor.close()
            raise RuntimeError("Could not create auto-directed video.")

        duration = self.sync.duration
        total_frames = max(1, int(duration * cfg.fps))
        current = 0
        last_cut_t = -999.0
        last_section = -1
        beat_count = 0

        try:
            for idx in range(total_frames):
                t = idx / cfg.fps
                state = self.sync.state(t)
                cut = False

                if self._is_near(t, self.sync.beat_times):
                    beat_count += 1
                    group = int(round(
                        cfg.beat_group_low_energy
                        - state.energy * (
                            cfg.beat_group_low_energy - cfg.beat_group_high_energy
                        )
                    ))
                    group = max(1, group)
                    if beat_count % group == 0:
                        cut = True

                if cfg.cut_on_sections and state.section != last_section:
                    cut = True

                if cfg.cut_on_drops and state.drop > 0.78:
                    cut = True

                elapsed = t - last_cut_t
                if elapsed < cfg.min_shot_seconds:
                    cut = False
                if elapsed >= cfg.max_shot_seconds:
                    cut = True

                if cut:
                    if len(cursors) > 1:
                        next_index = (current + 1 + state.section) % len(cursors)
                        if next_index == current:
                            next_index = (current + 1) % len(cursors)
                        current = next_index
                    last_cut_t = t

                last_section = state.section
                writer.write(cursors[current].frame(cfg.width, cfg.height))

                if progress and idx % 10 == 0:
                    progress(min(1.0, idx / total_frames))
        finally:
            writer.release()
            for cursor in cursors:
                cursor.close()

        return self.output_path
