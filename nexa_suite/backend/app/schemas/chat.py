"""Schemas for the real chat assistant endpoint."""

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=800)
    history: list[ChatHistoryItem] = Field(default_factory=list)
    source: str = "chat_page"
    address_style: str | None = Field(default=None, max_length=40)
    preferred_language: str = Field(default="auto", pattern="^(auto|Bangla|English|Mixed)$")
    whatsapp_draft_open_target: str | None = Field(default="auto", max_length=24)


class ChatWeatherSnapshot(BaseModel):
    location: str
    temperature_c: float | None = None
    condition: str | None = None
    wind_kph: float | None = None
    humidity_percent: int | None = None


class ChatSearchResult(BaseModel):
    title: str
    snippet: str = ""
    source_url: str | None = None
    provider: str
    confidence: str = "medium"


class ChatActionStatus(BaseModel):
    kind: str = "app"
    target: str
    label: str
    executed: bool = False
    requires_confirmation: bool = True
    message: str
    recipient: str | None = None
    draft_text: str | None = None
    action_label: str | None = None


class ChatPendingTask(BaseModel):
    kind: str
    status_label: str
    prompt: str
    recipient: str | None = None
    message: str | None = None
    expires_at: str | None = None


class ChatMessageResponse(BaseModel):
    status: str
    module: str = "chat"
    intent: str
    message: str
    answer: str
    blocked: bool = False
    requires_confirmation: bool = False
    execution_enabled: bool = False
    provider: str | None = None
    source: str | None = None
    source_url: str | None = None
    chips: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    weather: ChatWeatherSnapshot | None = None
    search_results: list[ChatSearchResult] = Field(default_factory=list)
    show_search_results_by_default: bool = False
    action: ChatActionStatus | None = None
    pending_task: ChatPendingTask | None = None
    confidence: str | None = None
    live_data: bool = False
    live_data_warning: bool = False
    auto_execute_safe: bool = False
    llm_used: bool = False
    llm_provider: str | None = None
    fallback_used: bool = False
    source_type: str = "local"
    route_debug: dict[str, object] | None = None
    error: str | None = None
