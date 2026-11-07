from pathlib import Path

from app.voice.vosk_config import get_vosk_stt_config


def check_vosk_dependency() -> tuple[bool, str]:
    try:
        import vosk  # noqa: F401
    except ImportError:
        return (
            False,
            "Vosk dependency is not installed. Install it with: pip install vosk",
        )
    return True, "Vosk dependency is installed."


def check_vosk_model_path() -> tuple[bool, str]:
    config = get_vosk_stt_config()
    model_path = Path(config.model_path)
    if not model_path.exists():
        return (
            False,
            "Vosk model path is missing. Place the model at models/vosk/bn.",
        )
    if not model_path.is_dir():
        return (
            False,
            "Vosk model path is not a directory. Place the model at models/vosk/bn.",
        )

    classic_subdirs = ["am", "conf", "graph"]
    streaming_subdirs = ["am-onnx", "lang"]

    classic_match = all((model_path / d).exists() for d in classic_subdirs)
    streaming_match = all((model_path / d).exists() for d in streaming_subdirs)

    if classic_match:
        return True, "Classic Vosk model path exists."
    if streaming_match:
        return True, "Vosk streaming ONNX model path exists."

    return False, (
        "Vosk model path exists but does not match classic or streaming model structure. "
        "Expected classic folders am/conf/graph or streaming folders am-onnx/lang."
    )


def get_vosk_readiness_status() -> dict:
    dep_ok, dep_msg = check_vosk_dependency()
    model_ok, model_msg = check_vosk_model_path()
    return {
        "dependency_installed": dep_ok,
        "dependency_message": dep_msg,
        "model_available": model_ok,
        "model_message": model_msg,
        "ready": dep_ok and model_ok,
    }
