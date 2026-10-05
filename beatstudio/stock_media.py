from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os
import requests

@dataclass
class StockVideo:
    id: str
    page_url: str
    creator: str
    creator_url: str
    preview_image: str
    video_url: str
    width: int
    height: int
    duration: float

class PexelsVideoCatalog:
    BASE="https://api.pexels.com/v1/videos"

    def __init__(self, api_key: Optional[str]=None):
        self.api_key=api_key or os.getenv("PEXELS_API_KEY")

    @property
    def configured(self):
        return bool(self.api_key)

    def search(self, query, *, orientation=None, size=None, per_page=15):
        if not self.api_key:
            raise RuntimeError("PEXELS_API_KEY is not configured.")
        params={"query":query,"per_page":max(1,min(80,per_page))}
        if orientation: params["orientation"]=orientation
        if size: params["size"]=size
        r=requests.get(f"{self.BASE}/search",headers={"Authorization":self.api_key},params=params,timeout=30)
        r.raise_for_status()
        out=[]
        for item in r.json().get("videos",[]):
            files=sorted(item.get("video_files") or [],key=lambda x:(x.get("width") or 0)*(x.get("height") or 0),reverse=True)
            best=files[0] if files else {}
            user=item.get("user") or {}
            out.append(StockVideo(
                id=str(item.get("id","")),page_url=str(item.get("url","")),creator=str(user.get("name","")),
                creator_url=str(user.get("url","")),preview_image=str(item.get("image","")),
                video_url=str(best.get("link","")),width=int(best.get("width") or item.get("width") or 0),
                height=int(best.get("height") or item.get("height") or 0),duration=float(item.get("duration") or 0)
            ))
        return out
