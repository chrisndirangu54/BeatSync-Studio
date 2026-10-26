"""Official Hyper3D Rodin submission and status/download adapters.

Never invoke paid generation implicitly during rendering.
"""
import os
import requests

class RodinClient:
    BASE="https://api.hyper3d.com/api/v2"
    def __init__(self, api_key=None, session=None):
        self.key=api_key or os.getenv("RODIN_API_KEY")
        self.http=session or requests.Session()
    def _headers(self):
        if not self.key: raise RuntimeError("RODIN_API_KEY is not configured")
        return {"Authorization":"Bearer "+self.key}
    def generate(self, prompt, *, t_pose=False, tier="Regular"):
        if not isinstance(prompt,str) or not 1<=len(prompt)<=1024: raise ValueError("Invalid 3D prompt")
        if tier not in {"Regular","Sketch","Detail","Smooth","Gen-2.5-Medium"}:
            raise ValueError("Unsupported Rodin tier")
        response=self.http.post(self.BASE+"/rodin",headers=self._headers(),
                                data={"prompt":prompt,"tier":tier,
                                      "TAPose":str(bool(t_pose)).lower(),
                                      "geometry_file_format":"glb"},timeout=60)
        response.raise_for_status()
        return response.json()
    def status(self, subscription_key):
        if not subscription_key: raise ValueError("Missing subscription key")
        r=self.http.post(self.BASE+"/status",headers=self._headers(),
                         json={"subscription_key":subscription_key},timeout=30)
        r.raise_for_status()
        return r.json()
    def download_links(self, task_uuid):
        if not task_uuid: raise ValueError("Missing Rodin task UUID")
        r=self.http.post(self.BASE+"/download",headers=self._headers(),
                         json={"task_uuid":task_uuid},timeout=30)
        r.raise_for_status()
        return r.json()

class MixamoAdapter:
    """Import Mixamo assets uploaded by the user; no undocumented/private API."""
    supported_character_formats=("glb",)
    supported_motion_formats=("bvh","fbx","glb")
    def capability(self):
        return {"mode":"licensed-file-import","public_api_verified":False,
                "human_autorig_only":True,
                "formats":list(self.supported_motion_formats)}

class HuggingFaceMotionAdapter:
    """Validated self-hosted motion-model configuration; no guessed hosted endpoints."""
    MODELS={"nvidia/Kimodo-SOMA-RP-v1.2":"human_text_motion",
            "kehong/MoCapAnythingV2-weights":"cross_species_retarget"}
    def __init__(self, model_id):
        if model_id not in self.MODELS: raise ValueError("Unsupported motion model")
        self.model_id=model_id
    def capability(self):
        return {"model_id":self.model_id,"task":self.MODELS[self.model_id],
                "execution":"external-model-worker-required"}
