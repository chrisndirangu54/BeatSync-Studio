from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os,time,requests

@dataclass
class VideoGenerationResult:
    task_id: str
    status: str="queued"
    video_url: Optional[str]=None
    raw: Optional[Dict[str,Any]]=None

class SeedanceClient:
    DEFAULT_BASE="https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks"
    DEFAULT_MODEL="dreamina-seedance-2-5-260628"

    def __init__(self,api_key:Optional[str]=None,base_url:Optional[str]=None):
        self.api_key=api_key or os.getenv("BYTEPLUS_ARK_API_KEY")
        self.base_url=base_url or os.getenv("SEEDANCE_API_BASE") or self.DEFAULT_BASE

    @property
    def configured(self):
        return bool(self.api_key)

    def _headers(self):
        if not self.api_key:
            raise RuntimeError("BYTEPLUS_ARK_API_KEY is not configured.")
        return {"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"}

    @staticmethod
    def _asset(url,kind,role):
        if kind=="image": return {"type":"image_url","image_url":{"url":url},"role":role}
        if kind=="video": return {"type":"video_url","video_url":{"url":url},"role":role}
        if kind=="audio": return {"type":"audio_url","audio_url":{"url":url},"role":role}
        raise ValueError(kind)

    def create(self,prompt,*,model=DEFAULT_MODEL,references=None,duration=8,resolution="1080p",ratio="adaptive",generate_audio=False,watermark=False,task_type="auto"):
        content=[{"type":"text","text":prompt}]
        for ref in references or []:
            content.append(self._asset(ref["url"],ref["kind"],ref.get("role",f"reference_{ref['kind']}")))
        payload={"model":model,"content":content,"generate_audio":generate_audio,"watermark":watermark,"resolution":resolution}
        if task_type in {"auto","reference","edit","extend"}:
            payload["omni_reference_task_type"]=task_type
        if task_type not in {"edit","extend"}:
            payload["duration"]=int(max(4,min(30,duration))); payload["ratio"]=ratio
        else:
            payload["duration"]=-1; payload["ratio"]="adaptive"
        r=requests.post(self.base_url,headers=self._headers(),json=payload,timeout=90)
        r.raise_for_status()
        data=r.json()
        return VideoGenerationResult(task_id=str(data["id"]),raw=data)

    def get(self,task_id):
        r=requests.get(f"{self.base_url}/{task_id}",headers=self._headers(),timeout=30)
        r.raise_for_status()
        data=r.json(); content=data.get("content") or {}
        video_url=content.get("video_url") or content.get("videoUrl")
        return VideoGenerationResult(task_id=task_id,status=str(data.get("status","")),video_url=str(video_url) if video_url else None,raw=data)

    def wait(self,result,*,poll_seconds=8,max_wait_seconds=900):
        deadline=time.time()+max_wait_seconds
        while time.time()<deadline:
            current=self.get(result.task_id)
            if current.status=="succeeded": return current
            if current.status in {"failed","cancelled","expired"}:
                raise RuntimeError(f"Seedance task ended with status={current.status}: {current.raw}")
            time.sleep(poll_seconds)
        raise TimeoutError("Timed out waiting for Seedance video generation.")

def download_video(url,destination):
    with requests.get(url,stream=True,timeout=180) as r:
        r.raise_for_status()
        with open(destination,"wb") as fh:
            for chunk in r.iter_content(1024*1024):
                if chunk: fh.write(chunk)
    return destination
