"""Command preview API routes for the Nexa AI backend."""

from fastapi import APIRouter

from app.schemas import CommandPreviewRequest
from app.schemas import CommandPreviewResponse
from app.schemas import CommandRouteHealth
from app.schemas import create_preview_response

router = APIRouter(prefix="/commands", tags=["commands"])


@router.get("/health", response_model=CommandRouteHealth)
def command_route_health() -> CommandRouteHealth:
    """Return health status for the command preview module."""
    return CommandRouteHealth(
        status="ok",
        module="command_preview",
        phase="15.2",
        execution_enabled=False,
    )


@router.post("/preview", response_model=CommandPreviewResponse)
def preview_command(
    request: CommandPreviewRequest,
) -> CommandPreviewResponse:
    """Return a preview-only response for a command understanding result.

    No real execution occurs. can_execute is always False.
    """
    return create_preview_response(request)
