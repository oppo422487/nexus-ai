import json
import wave
from pathlib import Path

from app.voice.vosk_config import get_vosk_stt_config
from app.voice.vosk_runtime import get_vosk_readiness_status


def get_vosk_test_wav_path() -> Path:
    config = get_vosk_stt_config()
    return Path(config.model_path) / "test.wav"


def transcribe_vosk_test_wav() -> dict:
    readiness = get_vosk_readiness_status()
    if not readiness["ready"]:
        return {
            "status": "not_ready",
            "transcribed": False,
            "text": "",
            "message": "Vosk STT is not ready.",
            "error": readiness.get("dependency_message")
            or readiness.get("model_message")
            or "Unknown reason",
        }

    wav_path = get_vosk_test_wav_path()
    if not wav_path.exists():
        return {
            "status": "failed",
            "transcribed": False,
            "text": "",
            "message": "Vosk test WAV transcription failed.",
            "error": "test.wav was not found in the model folder.",
        }

    try:
        from vosk import Model, KaldiRecognizer
    except ImportError as e:
        return {
            "status": "failed",
            "transcribed": False,
            "text": "",
            "message": "Vosk test WAV transcription failed.",
            "error": str(e),
        }

    config = get_vosk_stt_config()
    model_path = Path(config.model_path)

    try:
        model = Model(str(model_path))
    except Exception:
        return {
            "status": "failed",
            "transcribed": False,
            "text": "",
            "message": "Vosk test WAV transcription failed.",
            "error": "Vosk model could not be loaded by the current Python runtime. "
            "The downloaded model may use a streaming ONNX structure "
            "that requires a compatible runtime.",
        }

    try:
        with wave.open(str(wav_path), "rb") as wf:
            sample_rate = wf.getframerate()
            rec = KaldiRecognizer(model, sample_rate)

            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                rec.AcceptWaveform(data)

            final = json.loads(rec.FinalResult())
            text = final.get("text", "")

        return {
            "status": "completed",
            "transcribed": True,
            "text": text,
            "message": "Vosk test WAV transcription completed.",
            "error": None,
        }
    except Exception as e:
        return {
            "status": "failed",
            "transcribed": False,
            "text": "",
            "message": "Vosk test WAV transcription failed.",
            "error": str(e),
        }
