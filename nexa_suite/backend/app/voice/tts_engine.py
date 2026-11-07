"""Local offline TTS engine (Windows SAPI via pyttsx3).

TTS only speaks text it is given. It never executes commands and is
disabled by default in the permission center.
"""

from __future__ import annotations

import threading

MAX_TTS_TEXT_LENGTH = 400

_speak_lock = threading.Lock()


def check_tts_dependency() -> tuple[bool, str]:
    try:
        import pyttsx3  # noqa: F401
    except ImportError:
        return False, "pyttsx3 is not installed. Install it with: pip install pyttsx3"
    return True, "pyttsx3 dependency is installed."


def get_tts_status() -> dict:
    dep_ok, dep_msg = check_tts_dependency()
    voices: list[dict] = []
    error = None
    if dep_ok:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            for voice in engine.getProperty("voices"):
                voices.append(
                    {
                        "id": str(voice.id),
                        "name": str(voice.name),
                        "languages": [str(l) for l in (voice.languages or [])],
                    }
                )
            engine.stop()
        except Exception as exc:
            error = f"TTS voices could not be listed: {exc}"
    return {
        "dependency_installed": dep_ok,
        "dependency_message": dep_msg,
        "available": dep_ok and error is None,
        "voices": voices,
        "error": error,
    }


def speak_text(text: str, rate: int | None = None, voice_id: str | None = None) -> dict:
    """Speak text aloud through the local system voice. Never raises."""
    dep_ok, dep_msg = check_tts_dependency()
    if not dep_ok:
        return {"status": "not_ready", "spoken": False, "error": dep_msg}

    cleaned = (text or "").strip()
    if not cleaned:
        return {"status": "failed", "spoken": False, "error": "Text is empty."}
    if len(cleaned) > MAX_TTS_TEXT_LENGTH:
        cleaned = cleaned[:MAX_TTS_TEXT_LENGTH]

    try:
        with _speak_lock:
            import pyttsx3

            engine = pyttsx3.init()
            if rate is not None:
                safe_rate = max(80, min(int(rate), 300))
                engine.setProperty("rate", safe_rate)
            if voice_id:
                for voice in engine.getProperty("voices"):
                    if str(voice.id) == voice_id:
                        engine.setProperty("voice", voice.id)
                        break
            engine.say(cleaned)
            engine.runAndWait()
            engine.stop()
        return {"status": "completed", "spoken": True, "error": None}
    except Exception as exc:
        return {"status": "failed", "spoken": False, "error": f"TTS failed: {exc}"}
