"""Schemas for optional, permission-gated image generation."""

from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=800)
    width: int = Field(default=768, ge=256, le=1536)
    height: int = Field(default=768, ge=256, le=1536)
    user_confirmed: bool = False


class ImageGenerationResponse(BaseModel):
    status: str
    module: str = "image_generation"
    generated: bool = False
    prompt: str
    image_id: str | None = None
    image_url: str | None = None
    provider: str = "Hugging Face"
    model: str | None = None
    message: str
    error: str | None = None
