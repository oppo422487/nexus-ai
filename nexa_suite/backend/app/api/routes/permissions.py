"""API routes for the security/permission center."""

from fastapi import APIRouter

from app.permissions import (
    TOGGLEABLE_PERMISSIONS,
    LOCKED_PERMISSIONS,
    load_permissions,
    set_permission,
)
from app.schemas.permissions import (
    PermissionItem,
    PermissionsResponse,
    PermissionUpdateRequest,
    PermissionUpdateResponse,
)

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=PermissionsResponse)
def get_permissions() -> PermissionsResponse:
    current = load_permissions()
    items = [
        PermissionItem(
            key=key,
            label=meta["label"],
            description=meta["description"],
            enabled=current.get(key, bool(meta["default"])),
            locked=False,
        )
        for key, meta in TOGGLEABLE_PERMISSIONS.items()
    ]
    locked = [
        PermissionItem(
            key=key,
            label=meta["label"],
            description=meta["description"],
            enabled=False,
            locked=True,
        )
        for key, meta in LOCKED_PERMISSIONS.items()
    ]
    return PermissionsResponse(permissions=items, locked_permissions=locked)


@router.put("", response_model=PermissionUpdateResponse)
def update_permission(request: PermissionUpdateRequest) -> PermissionUpdateResponse:
    ok, message = set_permission(request.key, request.enabled)
    enabled_now = load_permissions().get(request.key, False)
    return PermissionUpdateResponse(
        status="ok" if ok else "blocked",
        key=request.key,
        enabled=enabled_now,
        updated=ok,
        message=message,
    )
