"""Same-origin facade for the private native voice-engine bridge."""
import os
import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/engine", tags=["native-engine"])


class EngineCommand(BaseModel):
    action: str = Field(max_length=40)
    text: str = Field(default="", max_length=20000)
    key: str = Field(default="", max_length=300)
    id: str = Field(default="", max_length=100)
    accepted: bool = False


async def forward(path, payload=None):
    token = os.getenv("NEXA_ENGINE_BRIDGE_TOKEN", "")
    if not token:
        raise HTTPException(503, "Start Nexa with start_nexa.cmd to connect the native engine.")
    try:
        async with httpx.AsyncClient(timeout=8, trust_env=False) as client:
            response = await client.request("GET" if payload is None else "POST",
                "http://127.0.0.1:8767" + path, json=payload,
                headers={"X-Nexa-Bridge": token})
        result = response.json()
        if response.status_code != 200:
            raise HTTPException(response.status_code, result.get("error", "Engine error"))
        return result
    except httpx.HTTPError:
        raise HTTPException(503, "Native engine is not running.")


@router.get("/events")
async def engine_events(after: int = 0):
    return await forward("/state?after=" + str(max(0, after)))


@router.get("/frame")
async def engine_camera_frame():
    token = os.getenv("NEXA_ENGINE_BRIDGE_TOKEN", "")
    if not token:
        raise HTTPException(503, "Native engine is not running.")
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            response = await client.get("http://127.0.0.1:8767/frame", headers={"X-Nexa-Bridge": token})
        if response.status_code != 200:
            raise HTTPException(404, "Camera is closed.")
        return Response(response.content, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    except httpx.HTTPError:
        raise HTTPException(503, "Camera is unavailable.")


@router.post("/command")
async def engine_command(body: EngineCommand, request: Request):
    # Engine control is available only to the local Nexa interface, not web pages.
    if request.headers.get("origin") not in {"http://127.0.0.1:8766", "http://localhost:8766"}:
        raise HTTPException(403, "Only the local Nexa interface can control this engine.")
    return await forward("/command", body.model_dump())
