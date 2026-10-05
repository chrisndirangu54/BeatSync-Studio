from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth
from pydantic import BaseModel

from beatstudio.plans import PLANS
from .auth import ADMIN_PERMISSIONS, Principal, require_admin, set_user_access

router = APIRouter(prefix="/v1/admin", tags=["admin"])

class UserRoleUpdate(BaseModel):
    role: str = "user"
    admin: bool = False
    permissions: list[str] = []

class UserPlanUpdate(BaseModel):
    plan: str

class DisableUserUpdate(BaseModel):
    disabled: bool

def serialize_user(user: auth.UserRecord) -> dict[str, Any]:
    claims = user.custom_claims or {}
    return {
        "uid": user.uid,
        "email": user.email,
        "display_name": user.display_name,
        "disabled": user.disabled,
        "email_verified": user.email_verified,
        "role": claims.get("role", "user"),
        "plan": claims.get("plan", "free"),
        "admin": bool(claims.get("admin", False)),
        "permissions": claims.get("permissions", []),
        "created_at": user.user_metadata.creation_timestamp,
        "last_sign_in_at": user.user_metadata.last_sign_in_timestamp,
    }

@router.get("/users")
def list_users(_: Principal = Depends(require_admin)):
    page = auth.list_users()
    users = []
    while page:
        users.extend(serialize_user(u) for u in page.users)
        page = page.get_next_page()
    return users

@router.get("/users/{uid}")
def get_user(uid: str, _: Principal = Depends(require_admin)):
    try:
        return serialize_user(auth.get_user(uid))
    except auth.UserNotFoundError:
        raise HTTPException(404, "User not found")

@router.patch("/users/{uid}/role")
def update_role(uid: str, body: UserRoleUpdate, current: Principal = Depends(require_admin)):
    if uid == current.uid and not body.admin:
        raise HTTPException(400, "You cannot remove your own admin access")
    user = auth.get_user(uid)
    bootstrap = os.getenv("BEATSYNC_BOOTSTRAP_ADMIN_EMAIL", "chrisndirangu54@gmail.com").lower()
    if user.email and user.email.lower() == bootstrap and not body.admin:
        raise HTTPException(400, "Bootstrap platform admin cannot be demoted")
    claims = set_user_access(
        uid,
        role=body.role,
        admin=body.admin,
        permissions=body.permissions if not body.admin else ADMIN_PERMISSIONS,
    )
    return {"uid": uid, "claims": claims}

@router.patch("/users/{uid}/plan")
def update_plan(uid: str, body: UserPlanUpdate, _: Principal = Depends(require_admin)):
    if body.plan not in PLANS:
        raise HTTPException(400, "Unknown plan")
    user = auth.get_user(uid)
    bootstrap = os.getenv("BEATSYNC_BOOTSTRAP_ADMIN_EMAIL", "chrisndirangu54@gmail.com").lower()
    if user.email and user.email.lower() == bootstrap and body.plan != "studio":
        raise HTTPException(400, "Bootstrap platform admin must retain Studio access")
    claims = set_user_access(uid, plan=body.plan)
    return {"uid": uid, "claims": claims}

@router.patch("/users/{uid}/disabled")
def disable_user(uid: str, body: DisableUserUpdate, current: Principal = Depends(require_admin)):
    if uid == current.uid and body.disabled:
        raise HTTPException(400, "You cannot disable your own account")
    user = auth.update_user(uid, disabled=body.disabled)
    return serialize_user(user)

@router.post("/users/{uid}/revoke-sessions")
def revoke_sessions(uid: str, current: Principal = Depends(require_admin)):
    if uid == current.uid:
        raise HTTPException(400, "Use normal sign-out for your own active session")
    auth.revoke_refresh_tokens(uid)
    return {"uid": uid, "revoked": True}

@router.delete("/users/{uid}")
def delete_user(uid: str, current: Principal = Depends(require_admin)):
    if uid == current.uid:
        raise HTTPException(400, "You cannot delete your own account")
    user = auth.get_user(uid)
    bootstrap = os.getenv("BEATSYNC_BOOTSTRAP_ADMIN_EMAIL", "chrisndirangu54@gmail.com").lower()
    if user.email and user.email.lower() == bootstrap:
        raise HTTPException(400, "Bootstrap platform admin cannot be deleted")
    auth.delete_user(uid)
    return {"uid": uid, "deleted": True}

@router.get("/permissions")
def permissions(_: Principal = Depends(require_admin)):
    return {"admin_permissions": ADMIN_PERMISSIONS}

@router.get("/provider-status")
def provider_status(_: Principal = Depends(require_admin)):
    names = [
        "SUNO_API_KEY","SUNO_GENERATE_URL","SUNO_EDIT_URL",
        "BYTEPLUS_ARK_API_KEY","PEXELS_API_KEY","JAMENDO_CLIENT_ID",
        "STRIPE_SECRET_KEY","STRIPE_WEBHOOK_SECRET",
    ]
    return {name: bool(os.getenv(name)) for name in names}
