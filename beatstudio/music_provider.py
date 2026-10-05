from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


class MusicProviderError(RuntimeError):
    pass


@dataclass
class MusicResult:
    provider: str
    audio_url: Optional[str] = None
    job_id: Optional[str] = None
    track_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class SunoClient:
    """
    Adapter for Suno's official developer API.

    Suno's API platform is authenticated and its endpoint paths can evolve.
    Configure the exact URLs from your Suno developer dashboard rather than
    baking undocumented or reverse-engineered routes into the application.

    Required:
      SUNO_API_KEY
      SUNO_GENERATE_URL

    Optional:
      SUNO_EDIT_URL
      SUNO_STATUS_URL_TEMPLATE   e.g. an official status URL containing {job_id}
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        generate_url: Optional[str] = None,
        edit_url: Optional[str] = None,
        status_url_template: Optional[str] = None,
        timeout: int = 90,
    ):
        self.api_key = api_key or os.getenv("SUNO_API_KEY")
        self.generate_url = generate_url or os.getenv("SUNO_GENERATE_URL")
        self.edit_url = edit_url or os.getenv("SUNO_EDIT_URL")
        self.status_url_template = status_url_template or os.getenv("SUNO_STATUS_URL_TEMPLATE")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.generate_url)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise MusicProviderError("SUNO_API_KEY is not configured.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _find_first(data: Any, keys) -> Optional[Any]:
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key]:
                    return data[key]
            for value in data.values():
                hit = SunoClient._find_first(value, keys)
                if hit:
                    return hit
        elif isinstance(data, list):
            for item in data:
                hit = SunoClient._find_first(item, keys)
                if hit:
                    return hit
        return None

    @classmethod
    def _normalize(cls, data: Dict[str, Any]) -> MusicResult:
        audio_url = cls._find_first(
            data,
            ("audio_url", "audioUrl", "download_url", "downloadUrl", "stream_url", "streamUrl"),
        )
        job_id = cls._find_first(data, ("job_id", "jobId", "task_id", "taskId", "id"))
        track_id = cls._find_first(data, ("track_id", "trackId", "song_id", "songId"))
        return MusicResult(
            provider="suno",
            audio_url=str(audio_url) if audio_url else None,
            job_id=str(job_id) if job_id else None,
            track_id=str(track_id) if track_id else None,
            raw=data,
        )

    def generate(
        self,
        prompt: str,
        *,
        model: str = "v6",
        instrumental: bool = False,
        title: Optional[str] = None,
        lyrics: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> MusicResult:
        if not self.generate_url:
            raise MusicProviderError("SUNO_GENERATE_URL is not configured.")

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "instrumental": instrumental,
        }
        if title:
            payload["title"] = title
        if lyrics:
            payload["lyrics"] = lyrics
        if extra:
            payload.update(extra)

        response = requests.post(
            self.generate_url,
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        if not response.ok:
            raise MusicProviderError(
                f"Suno generation failed ({response.status_code}): {response.text[:1200]}"
            )
        return self._normalize(response.json())

    def edit(
        self,
        instruction: str,
        *,
        source_track_id: Optional[str] = None,
        source_audio_url: Optional[str] = None,
        model: str = "v6",
        extra: Optional[Dict[str, Any]] = None,
    ) -> MusicResult:
        if not self.edit_url:
            raise MusicProviderError("SUNO_EDIT_URL is not configured.")

        payload: Dict[str, Any] = {
            "instruction": instruction,
            "model": model,
        }
        if source_track_id:
            payload["source_track_id"] = source_track_id
        if source_audio_url:
            payload["source_audio_url"] = source_audio_url
        if extra:
            payload.update(extra)

        response = requests.post(
            self.edit_url,
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        if not response.ok:
            raise MusicProviderError(
                f"Suno edit failed ({response.status_code}): {response.text[:1200]}"
            )
        return self._normalize(response.json())

    def wait_for_audio(
        self,
        result: MusicResult,
        *,
        poll_seconds: float = 3.0,
        max_wait_seconds: float = 300.0,
    ) -> MusicResult:
        if result.audio_url:
            return result
        if not result.job_id or not self.status_url_template:
            return result

        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            url = self.status_url_template.format(job_id=result.job_id)
            response = requests.get(url, headers=self._headers(), timeout=self.timeout)
            if response.ok:
                current = self._normalize(response.json())
                if current.audio_url:
                    return current
            time.sleep(poll_seconds)
        raise MusicProviderError("Timed out waiting for Suno to return an audio URL.")


def download_audio(url: str, destination: str, timeout: int = 180) -> str:
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with open(destination, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return destination
