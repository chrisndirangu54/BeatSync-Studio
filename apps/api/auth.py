from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import firebase_admin
from fastapi import Depends, Header, HTTPException
from firebase_admin import auth, credentials

ADMIN_EMAIL = os.getenv("BEATSYNC_BOOTSTRAP_ADMIN_EMAIL", "chrisndirangu54@gmail.com").strip().lower()

ADMIN_PERMISSIONS = [
    "users.read",
    "users.write",
    "users.roles",
    "auth.sessions.revoke",
    "renders.read",
    "renders.manage",
    "plans.read",
    "plans.manage",
    "billing.read",
    "billing.manage",
    "providers.read",
    "providers.manage",
    "audit.read",
]

@dataclass
class Principal:
    uid: str
    email: str | None
    email_verified: bool
    role: str
    admin: bool
    plan: str
    permissions: list[str]
    claims: dict

def _init_firebase():
    if firebase_admin._apps:
        return
    project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        import json
        info = json.loads(service_account_json)
        firebase_admin.initialize_app(
            credentials.Certificate(info),
            {"projectId": project_id or info.get("project_id")},
        )
    else:
        firebase_admin.initialize_app(options={"projectId": project_id} if project_id else None)

_init_firebase()

def _principal_from_claims(claims: dict) -> Principal:
    admin = bool(claims.get("admin", False))
    role = str(claims.get("role") or ("admin" if admin else "user"))
    permissions = list(claims.get("permissions") or (ADMIN_PERMISSIONS if admin else []))
    return Principal(
        uid=str(claims.get("uid") or claims.get("sub")),
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified", False)),
        role=role,
        admin=admin,
        plan=str(claims.get("plan") or ("studio" if admin else "free")),
        permissions=permissions,
        claims=claims,
    )

def _merge_custom_claims(uid: str, updates: dict) -> dict:
    user = auth.get_user(uid)
    claims = dict(user.custom_claims or {})
    claims.update(updates)
    auth.set_custom_user_claims(uid, claims)
    return claims

def _maybe_bootstrap_admin(claims: dict):
    email = str(claims.get("email") or "").lower()
    if (
        email
        and email == ADMIN_EMAIL
        and bool(claims.get("email_verified", False))
        and not bool(claims.get("admin", False))
    ):
        uid = str(claims.get("uid") or claims.get("sub"))
        updates = {
            "admin": True,
            "role": "admin",
            "plan": "studio",
            "permissions": ADMIN_PERMISSIONS,
        }
        _merge_custom_claims(uid, updates)
        claims = dict(claims)
        claims.update(updates)
    return claims

def require_user(authorization: str = Header(default="")) -> Principal:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Firebase bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = auth.verify_id_token(token, check_revoked=True)
        claims = _maybe_bootstrap_admin(claims)
        return _principal_from_claims(claims)
    except auth.RevokedIdTokenError:
        raise HTTPException(401, "Session revoked")
    except Exception:
        raise HTTPException(401, "Invalid or expired Firebase token")

def require_admin(user: Principal = Depends(require_user)) -> Principal:
    if not user.admin:
        raise HTTPException(403, "Administrator access required")
    return user

def require_permission(permission: str):
    def dependency(user: Principal = Depends(require_user)):
        if user.admin or permission in user.permissions:
            return user
        raise HTTPException(403, f"Missing permission: {permission}")
    return dependency

def set_user_access(
    uid: str,
    *,
    role: str | None = None,
    plan: str | None = None,
    permissions: Iterable[str] | None = None,
    admin: bool | None = None,
):
    updates = {}
    if role is not None:
        updates["role"] = role
    if plan is not None:
        updates["plan"] = plan
    if admin is not None:
        updates["admin"] = bool(admin)
        if admin:
            updates.setdefault("role", "admin")
            updates.setdefault("plan", "studio")
            updates.setdefault("permissions", ADMIN_PERMISSIONS)
    if permissions is not None:
        updates["permissions"] = list(permissions)
    return _merge_custom_claims(uid, updates)
