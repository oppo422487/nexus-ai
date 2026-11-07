from dataclasses import dataclass, field
from app.core.runtime_paths import models_dir



def _default_model_path() -> str:
    # Resolve relative to the backend folder so readiness does not depend
    # on the process working directory.
    return str(models_dir() / "vosk" / "bn")


@dataclass
class VoskSTTConfig:
    enabled: bool = False
    engine: str = "vosk"
    mode: str = "local_offline"
    model_path: str = field(default_factory=_default_model_path)
    sample_rate: int = 16000
    language: str = "bn-BD"
    auto_start: bool = False
    message: str = "Vosk STT is prepared but disabled until model and dependency are installed."


def get_vosk_stt_config() -> VoskSTTConfig:
    return VoskSTTConfig()
