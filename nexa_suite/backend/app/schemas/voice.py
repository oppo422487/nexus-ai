from pydantic import BaseModel


class VoiceSTTStatusResponse(BaseModel):
    status: str = "ok"
    module: str = "voice_stt"
    phase: str = "34.2"
    engine: str
    mode: str
    enabled: bool
    model_path: str
    sample_rate: int
    language: str
    auto_start: bool
    dependency_required: str = "AssemblyAI API"
    model_required: bool = False
    execution_enabled: bool = False
    message: str


class VoiceSTTReadinessResponse(BaseModel):
    status: str = "ok"
    module: str = "voice_stt_readiness"
    phase: str = "34.3"
    engine: str = "assemblyai_streaming"
    dependency_installed: bool
    dependency_message: str
    model_available: bool
    model_message: str
    ready: bool
    execution_enabled: bool = False
    message: str


class VoiceSTTTestTranscriptionResponse(BaseModel):
    status: str
    module: str = "voice_stt_test_transcription"
    phase: str = "34.4"
    engine: str = "assemblyai_streaming"
    transcribed: bool = False
    text: str = ""
    execution_enabled: bool = False
    message: str
    error: str | None = None


class VoiceSTTEngineInfo(BaseModel):
    name: str
    label: str
    dependency_installed: bool
    model_available: bool
    ready: bool
    message: str


class VoiceSTTEnginesResponse(BaseModel):
    status: str = "ok"
    module: str = "voice_stt_engines"
    preferred_engine: str
    engines: list[VoiceSTTEngineInfo]
    execution_enabled: bool = False
    message: str = "STT engine overview loaded."


class VoiceTranscriptionResponse(BaseModel):
    status: str
    module: str = "voice_stt_transcription"
    engine: str = "none"
    transcribed: bool = False
    text: str = ""
    language: str | None = None
    execution_enabled: bool = False
    message: str = ""
    warning: str | None = None
    error: str | None = None


class TTSVoiceInfo(BaseModel):
    id: str
    name: str
    languages: list[str] = []


class TTSStatusResponse(BaseModel):
    status: str = "ok"
    module: str = "voice_tts"
    dependency_installed: bool
    available: bool
    enabled: bool
    voices: list[TTSVoiceInfo] = []
    execution_enabled: bool = False
    message: str = ""
    error: str | None = None


class TTSSpeakRequest(BaseModel):
    text: str
    rate: int | None = None
    voice_id: str | None = None


class TTSSpeakResponse(BaseModel):
    status: str
    module: str = "voice_tts"
    spoken: bool = False
    execution_enabled: bool = False
    message: str = ""
    error: str | None = None


class EdgeTTSRequest(BaseModel):
    text: str
    voice: str = "bn-BD-NabanitaNeural"
    rate: str = "+0%"
