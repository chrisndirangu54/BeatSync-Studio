from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import cv2
import numpy as np

@dataclass
class SceneProfile:
    path: str
    people: float = 0.0
    faces: float = 0.0
    performers: float = 0.0
    dancing: float = 0.0
    cars: float = 0.0
    landscapes: float = 0.0
    closeup: float = 0.0
    wide: float = 0.0
    motion: float = 0.0
    emotion: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

class SceneUnderstanding:
    CLIP_LABELS = [
        "musician performing on stage", "person dancing", "car driving",
        "scenic landscape", "city street", "intimate emotional close-up",
        "wide cinematic shot", "joyful happy scene", "sad emotional scene",
        "angry intense scene", "calm reflective scene",
    ]

    def __init__(self, object_model="yolo11n.pt", use_clip=True, clip_model="openai/clip-vit-base-patch32"):
        self.object_model_name = object_model
        self.use_clip = use_clip
        self.clip_model_name = clip_model
        self._detector = None
        self._clip_model = None
        self._clip_processor = None
        self._face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def _load_yolo(self):
        if self._detector is None:
            try:
                from ultralytics import YOLO
                self._detector = YOLO(self.object_model_name)
            except Exception:
                self._detector = False
        return self._detector

    def _load_clip(self):
        if not self.use_clip:
            return False
        if self._clip_model is None:
            try:
                from transformers import CLIPModel, CLIPProcessor
                self._clip_processor = CLIPProcessor.from_pretrained(self.clip_model_name)
                self._clip_model = CLIPModel.from_pretrained(self.clip_model_name)
            except Exception:
                self._clip_model = False
                self._clip_processor = False
        return self._clip_model

    @staticmethod
    def _sample_frames(path, samples=8):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return []
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        ids = np.linspace(0, max(0, total - 1), max(2, samples)).astype(int)
        frames = []
        for idx in ids:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
        cap.release()
        return frames

    @staticmethod
    def _motion_score(frames):
        if len(frames) < 2:
            return 0.0
        scores = []
        prev = cv2.cvtColor(cv2.resize(frames[0], (320, 180)), cv2.COLOR_BGR2GRAY)
        for frame in frames[1:]:
            cur = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(prev, cur, None, .5, 3, 15, 3, 5, 1.2, 0)
            mag = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            scores.append(float(np.percentile(mag, 75)))
            prev = cur
        return float(np.clip(np.mean(scores) / 8.0, 0, 1))

    def _clip_scores(self, frame):
        model = self._load_clip()
        if model is False:
            return {}
        try:
            import torch
            from PIL import Image
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            inputs = self._clip_processor(text=self.CLIP_LABELS, images=image, return_tensors="pt", padding=True)
            with torch.no_grad():
                probs = model(**inputs).logits_per_image.softmax(dim=1)[0].cpu().numpy()
            return {label: float(prob) for label, prob in zip(self.CLIP_LABELS, probs)}
        except Exception:
            return {}

    def analyze(self, path, samples=8):
        frames = self._sample_frames(path, samples)
        p = SceneProfile(path=path)
        if not frames:
            return p
        h0, w0 = frames[0].shape[:2]
        frame_area = max(1, h0*w0)
        person_areas, people_counts, car_counts, face_counts = [], [], [], []
        semantic = {k: [] for k in self.CLIP_LABELS}
        detector = self._load_yolo()
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_counts.append(len(self._face.detectMultiScale(gray, 1.2, 4, minSize=(30,30))))
            if detector is not False:
                try:
                    result = detector.predict(frame, verbose=False, conf=.28)[0]
                    pc = cc = 0
                    for box in result.boxes:
                        cls = int(box.cls.item())
                        name = str(result.names.get(cls, cls)).lower()
                        x1,y1,x2,y2 = box.xyxy[0].cpu().numpy().tolist()
                        if name == "person":
                            pc += 1
                            person_areas.append(float(max(0,x2-x1)*max(0,y2-y1)/frame_area))
                        elif name in {"car","truck","bus","motorcycle"}:
                            cc += 1
                    people_counts.append(pc); car_counts.append(cc)
                except Exception:
                    people_counts.append(0); car_counts.append(0)
            for k,v in self._clip_scores(frame).items():
                semantic[k].append(v)
        p.motion = self._motion_score(frames)
        p.people = float(np.clip(np.mean(people_counts or [0])/3.0, 0, 1))
        p.faces = float(np.clip(np.mean(face_counts or [0])/2.0, 0, 1))
        p.cars = float(np.clip(np.mean(car_counts or [0])/2.0, 0, 1))
        area = float(np.mean(person_areas or [0]))
        p.closeup = float(np.clip((area-.14)/.30,0,1))
        p.wide = float(np.clip(1-area*3.0,0,1))
        sem = {k:(float(np.mean(v)) if v else 0.0) for k,v in semantic.items()}
        p.performers = sem["musician performing on stage"]
        p.dancing = float(np.clip(.60*sem["person dancing"] + .40*p.motion*p.people,0,1))
        p.landscapes = sem["scenic landscape"]
        p.closeup = max(p.closeup, sem["intimate emotional close-up"])
        p.wide = max(p.wide, sem["wide cinematic shot"])
        p.emotion = {
            "joyful": sem["joyful happy scene"], "sad": sem["sad emotional scene"],
            "intense": sem["angry intense scene"], "calm": sem["calm reflective scene"],
        }
        scores = {"performance":p.performers,"dancing":p.dancing,"cars":p.cars,"landscape":p.landscapes,
                  "closeup":p.closeup,"wide":p.wide,"motion":p.motion,**p.emotion}
        p.tags = [k for k,v in sorted(scores.items(), key=lambda x:x[1], reverse=True) if v>.18][:6]
        return p

def music_scene_score(profile, state, previous_index=None, index=0):
    high = float(np.clip(.45*state.energy + .35*state.bass + .20*state.drop,0,1))
    calm = 1-high
    score = high*(.28*profile.dancing + .18*profile.performers + .18*profile.motion + .12*profile.cars + .10*profile.emotion.get("intense",0))
    score += calm*(.22*profile.closeup + .18*profile.landscapes + .14*profile.emotion.get("calm",0) + .10*profile.emotion.get("sad",0) + .08*profile.wide)
    score += state.treble*.08*profile.wide + state.mids*.08*profile.faces
    if state.drop>.75:
        score += .25*max(profile.dancing, profile.motion, profile.cars)
    if previous_index is not None and index==previous_index:
        score -= .18
    return float(score)
