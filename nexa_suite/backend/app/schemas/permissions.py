"""Schemas for the security/permission center."""

from pydantic import BaseModel


class PermissionItem(BaseModel):
    key: str
    label: str
    description: str
    enabled: bool
    locked: bool = False


class PermissionsResponse(BaseModel):
    status: str = "ok"
    module: str = "permission_center"
    permissions: list[PermissionItem]
    locked_permissions: list[PermissionItem]
    message: str = "Permission center state loaded."


class PermissionUpdateRequest(BaseModel):
    key: str
    enabled: bool


class PermissionUpdateResponse(BaseModel):
    status: str
    key: str
    enabled: bool
    updated: bool
    message: str
