"""Selenium-backed, permission-gated YouTube playback controller.

The controller owns one Chrome session and only exposes a small, typed set of
media operations.  It never evaluates user-provided JavaScript or arbitrary
URLs.  Selenium is optional so the rest of Nexa can start without it.
"""

from __future__ import annotations

import re
import threading
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    _SELENIUM_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on optional runtime package
    webdriver = None  # type: ignore[assignment]
    WebDriverException = Exception  # type: ignore[assignment,misc]
    Options = None  # type: ignore[assignment]
    By = None  # type: ignore[assignment]
    WebDriverWait = None  # type: ignore[assignment]
    EC = None  # type: ignore[assignment]
    _SELENIUM_AVAILABLE = False


class YouTubeControllerError(RuntimeError):
    """A recoverable YouTube controller failure."""


@dataclass(frozen=True)
class ParsedYouTubeCommand:
    action: str
    query: str | None = None
    value: float | None = None
    enabled: bool | None = None


_NUMBER_RE = re.compile(r"(-?\d+(?:\.\d+)?)")


def _number(text: str) -> float | None:
    match = _NUMBER_RE.search(text)
    return float(match.group(1)) if match else None


def _clean_query(text: str) -> str:
    cleaned = text.lower().strip()
    patterns = (
        r"^(?:(?:youtube|yt)\s+(?:e|te)?\s*|ইউটিউব\s+(?:এ|তে)\s*|ইউটিউব(?:ে|তে)?\s*)",
        r"^(?:play|search|find|চালাও|চালু করো|খুঁজে দাও|search koro)\s+",
        r"\s+(?:on youtube|youtube e|youtube te|ইউটিউবে)\s*$",
        r"\s+(?:search koro|search করো|search dao|search দাও|খুঁজে দাও|খোঁজো|chalao|চালাও|play koro|play করো)\s*$",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split())


def parse_youtube_command(command: str) -> ParsedYouTubeCommand:
    """Parse English, Banglish, or Bangla media commands deterministically."""

    raw = " ".join((command or "").strip().split())
    text = raw.lower()
    if not text:
        return ParsedYouTubeCommand("status")

    if any(token in text for token in ("cancel timer", "timer cancel", "টাইমার বাতিল")):
        return ParsedYouTubeCommand("cancel_timer")
    if any(token in text for token in ("sleep timer", "timer set", "ঘুমের টাইমার")):
        return ParsedYouTubeCommand("sleep_timer", value=_number(text) or 30)
    if any(token in text for token in ("close youtube", "youtube close", "ইউটিউব বন্ধ")):
        return ParsedYouTubeCommand("close")
    if any(token in text for token in ("youtube status", "player status", "কি চলছে", "ki cholche")):
        return ParsedYouTubeCommand("status")
    if any(token in text for token in ("previous video", "আগের ভিডিও", "ager video")):
        return ParsedYouTubeCommand("previous")
    if any(token in text for token in ("next video", "পরের ভিডিও", "porer video")):
        return ParsedYouTubeCommand("next")
    if any(token in text for token in ("skip back", "rewind", "পিছনে", "pichone")):
        return ParsedYouTubeCommand("skip", value=-abs(_number(text) or 10))
    if any(token in text for token in ("skip", "forward", "সামনে", "samne")):
        return ParsedYouTubeCommand("skip", value=abs(_number(text) or 10))
    if any(token in text for token in ("speed", "গতি", "স্পিড")):
        return ParsedYouTubeCommand("set_speed", value=_number(text) or 1)
    if any(token in text for token in ("volume", "ভলিউম", "শব্দ")) and _number(text) is not None:
        return ParsedYouTubeCommand("set_volume", value=_number(text))
    if any(token in text for token in ("unmute", "sound on", "শব্দ চালু")):
        return ParsedYouTubeCommand("unmute")
    if any(token in text for token in ("mute", "sound off", "শব্দ বন্ধ")):
        return ParsedYouTubeCommand("mute")
    if any(token in text for token in ("fullscreen", "full screen", "ফুলস্ক্রিন")):
        return ParsedYouTubeCommand("fullscreen")
    if any(token in text for token in ("caption", "subtitle", "সাবটাইটেল")):
        enabled = not any(token in text for token in ("off", "বন্ধ"))
        return ParsedYouTubeCommand("captions", enabled=enabled)
    if any(token in text for token in ("theater", "theatre", "থিয়েটার")):
        return ParsedYouTubeCommand("theater")
    if "ambient" in text:
        return ParsedYouTubeCommand("ambient")
    if "autoplay" in text or "অটোপ্লে" in text:
        enabled = not any(token in text for token in ("off", "বন্ধ"))
        return ParsedYouTubeCommand("autoplay", enabled=enabled)
    if any(token in text for token in ("pause", "থামাও", "birti", "বিরতি")):
        return ParsedYouTubeCommand("pause")
    if any(token in text for token in ("resume", "unpause", "আবার চালাও", "abar chalao")):
        return ParsedYouTubeCommand("resume")
    if any(token in text for token in ("youtube search", "search youtube", "youtube e", "youtube te", "yt e", "yt te", "ইউটিউবে", "ইউটিউব এ", "ইউটিউবতে")):
        return ParsedYouTubeCommand("search", query=_clean_query(raw))
    if text.startswith(("play ", "চালাও ", "chalao ")):
        return ParsedYouTubeCommand("launch", query=_clean_query(raw))
    if text in {
        "youtube",
        "open youtube",
        "youtube open",
        "youtube open koro",
        "youtube kholo",
        "youtube khulo",
        "ইউটিউব খোলো",
        "ইউটিউব খুলে দাও",
    }:
        return ParsedYouTubeCommand("launch")
    return ParsedYouTubeCommand("launch", query=_clean_query(raw))


class YouTubeController:
    """Own a controlled Chrome window and manipulate only its video player."""

    VIDEO_SELECTOR = "video.html5-main-video"

    def __init__(self) -> None:
        self._driver: Any | None = None
        self._lock = threading.RLock()
        self._timer: threading.Timer | None = None
        self._timer_deadline: float | None = None
        self._pre_duck_volume = 100

    @property
    def available(self) -> bool:
        return _SELENIUM_AVAILABLE

    def _build_driver(self) -> Any:
        if not _SELENIUM_AVAILABLE:
            raise YouTubeControllerError(
                "Advanced YouTube control needs the optional selenium package."
            )
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        try:
            return webdriver.Chrome(options=options)
        except Exception as exc:  # pragma: no cover - requires local Chrome
            raise YouTubeControllerError(
                "Chrome could not start. Install/update Google Chrome and try again."
            ) from exc

    def _alive(self) -> bool:
        if self._driver is None:
            return False
        try:
            _ = self._driver.current_url
            return True
        except Exception:
            self._driver = None
            return False

    def _require_player(self) -> Any:
        if not self._alive():
            raise YouTubeControllerError("YouTube is not open. Play or search for a video first.")
        try:
            return self._driver.find_element(By.CSS_SELECTOR, self.VIDEO_SELECTOR)
        except Exception as exc:
            raise YouTubeControllerError("No playable YouTube video is active yet.") from exc

    def _js(self, script: str, *args: Any) -> Any:
        if not self._alive():
            raise YouTubeControllerError("YouTube is not open.")
        try:
            return self._driver.execute_script(script, *args)
        except Exception as exc:
            raise YouTubeControllerError("YouTube did not accept that player command.") from exc

    def launch(self, query: str | None = None) -> str:
        with self._lock:
            if not self._alive():
                self._driver = self._build_driver()
            if not query:
                self._driver.get("https://www.youtube.com")
                return "YouTube opened in the controlled player window."
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
            self._driver.get(url)
            try:
                result = WebDriverWait(self._driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "ytd-video-renderer a#video-title"))
                )
                self._driver.execute_script("arguments[0].click();", result)
                WebDriverWait(self._driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.VIDEO_SELECTOR))
                )
            except Exception as exc:
                raise YouTubeControllerError(
                    f"YouTube search opened, but no playable result was found for '{query}'."
                ) from exc
            return f"Playing '{query}' in the controlled YouTube window."

    def search(self, query: str) -> str:
        if not query.strip():
            raise YouTubeControllerError("Tell me what to search for on YouTube.")
        return self.launch(query.strip())

    def play(self) -> str:
        video = self._require_player()
        self._js("arguments[0].play();", video)
        return "YouTube playback resumed."

    def pause(self) -> str:
        video = self._require_player()
        self._js("arguments[0].pause();", video)
        return "YouTube playback paused."

    def skip(self, seconds: float) -> str:
        seconds = max(-3600, min(3600, float(seconds)))
        video = self._require_player()
        self._js(
            "arguments[0].currentTime=Math.max(0,Math.min(arguments[0].duration||Infinity,arguments[0].currentTime+arguments[1]));",
            video,
            seconds,
        )
        direction = "forward" if seconds >= 0 else "back"
        return f"Skipped {direction} {abs(seconds):g} seconds."

    def set_volume(self, percent: float) -> str:
        value = int(max(0, min(100, percent)))
        video = self._require_player()
        self._js("arguments[0].volume=arguments[1]/100; arguments[0].muted=false;", video, value)
        return f"YouTube volume set to {value}%."

    def set_muted(self, muted: bool) -> str:
        video = self._require_player()
        self._js("arguments[0].muted=arguments[1];", video, muted)
        return "YouTube muted." if muted else "YouTube unmuted."

    def set_speed(self, rate: float) -> str:
        allowed = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
        nearest = min(allowed, key=lambda item: abs(item - float(rate)))
        video = self._require_player()
        self._js("arguments[0].playbackRate=arguments[1];", video, nearest)
        return f"Playback speed set to {nearest:g}x."

    def _click(self, selector: str, label: str) -> str:
        if not self._alive():
            raise YouTubeControllerError("YouTube is not open.")
        try:
            element = self._driver.find_element(By.CSS_SELECTOR, selector)
            self._driver.execute_script("arguments[0].click();", element)
            return label
        except Exception as exc:
            raise YouTubeControllerError(f"The YouTube {label.lower()} control is unavailable.") from exc

    def set_captions(self, enabled: bool | None) -> str:
        if enabled is None:
            return self._click(".ytp-subtitles-button", "Captions toggled.")
        if not self._alive():
            raise YouTubeControllerError("YouTube is not open.")
        try:
            button = self._driver.find_element(By.CSS_SELECTOR, ".ytp-subtitles-button")
            current = button.get_attribute("aria-pressed") == "true"
            if current != enabled:
                self._driver.execute_script("arguments[0].click();", button)
            return f"Captions {'enabled' if enabled else 'disabled'}."
        except Exception as exc:
            raise YouTubeControllerError("Captions are unavailable for this video.") from exc

    def set_autoplay(self, enabled: bool | None) -> str:
        if not self._alive():
            raise YouTubeControllerError("YouTube is not open.")
        try:
            button = self._driver.find_element(By.CSS_SELECTOR, ".ytp-autonav-toggle-button")
            current = button.get_attribute("aria-checked") == "true"
            if enabled is None or current != enabled:
                self._driver.execute_script("arguments[0].click();", button)
            state = enabled if enabled is not None else not current
            return f"Autoplay {'enabled' if state else 'disabled'}."
        except Exception as exc:
            raise YouTubeControllerError("Autoplay control is unavailable.") from exc

    def toggle_ambient(self) -> str:
        if not self._alive():
            raise YouTubeControllerError("YouTube is not open.")
        try:
            settings = self._driver.find_element(By.CSS_SELECTOR, ".ytp-settings-button")
            self._driver.execute_script("arguments[0].click();", settings)
            items = WebDriverWait(self._driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ytp-menuitem"))
            )
            for item in items:
                if "ambient" in (item.text or "").lower():
                    self._driver.execute_script("arguments[0].click();", item)
                    return "Ambient mode toggled."
            raise YouTubeControllerError("Ambient mode is unavailable for this video or browser theme.")
        except YouTubeControllerError:
            raise
        except Exception as exc:
            raise YouTubeControllerError("Ambient mode control is unavailable.") from exc

    def set_sleep_timer(self, minutes: float) -> str:
        minutes = max(0.1, min(1440, float(minutes)))
        self.cancel_sleep_timer(silent=True)
        self._timer_deadline = time.time() + minutes * 60
        self._timer = threading.Timer(minutes * 60, self._timer_finished)
        self._timer.daemon = True
        self._timer.start()
        return f"YouTube sleep timer set for {minutes:g} minutes."

    def _timer_finished(self) -> None:
        try:
            self.pause()
        except Exception:
            pass
        finally:
            self._timer = None
            self._timer_deadline = None

    def cancel_sleep_timer(self, silent: bool = False) -> str:
        if self._timer:
            self._timer.cancel()
        self._timer = None
        self._timer_deadline = None
        return "YouTube sleep timer cancelled." if not silent else ""

    def duck(self, percent: float = 8) -> str:
        state = self.state()
        if not state["launched"]:
            return "YouTube is not open; audio ducking was not needed."
        self._pre_duck_volume = int(state["volume"])
        self.set_volume(percent)
        return f"YouTube volume ducked to {int(percent)}%."

    def restore(self) -> str:
        return self.set_volume(self._pre_duck_volume)

    def close(self) -> str:
        with self._lock:
            self.cancel_sleep_timer(silent=True)
            if self._driver is not None:
                try:
                    self._driver.quit()
                except Exception:
                    pass
            self._driver = None
        return "Controlled YouTube window closed."

    def state(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "available": self.available,
            "launched": False,
            "playing": False,
            "muted": False,
            "title": "",
            "current_time": 0,
            "duration": 0,
            "volume": 100,
            "playback_rate": 1,
            "timer_remaining_seconds": None,
            "current_url": "",
        }
        if self._timer_deadline is not None:
            base["timer_remaining_seconds"] = max(0, int(self._timer_deadline - time.time()))
        if not self._alive():
            return base
        base["launched"] = True
        try:
            base["current_url"] = str(self._driver.current_url or "")
            base["title"] = str(self._driver.title or "").removesuffix(" - YouTube")
            video = self._driver.find_element(By.CSS_SELECTOR, self.VIDEO_SELECTOR)
            values = self._js(
                "const v=arguments[0]; return {playing:!v.paused&&!v.ended,muted:v.muted,current_time:v.currentTime||0,duration:Number.isFinite(v.duration)?v.duration:0,volume:Math.round(v.volume*100),playback_rate:v.playbackRate||1};",
                video,
            )
            if isinstance(values, dict):
                base.update(values)
        except Exception:
            pass
        return base

    def execute(self, parsed: ParsedYouTubeCommand) -> str:
        action = parsed.action
        if action in {"launch", "search"}:
            return self.launch(parsed.query)
        if action == "play" or action == "resume":
            return self.play()
        if action == "pause":
            return self.pause()
        if action == "toggle_play":
            return self.pause() if self.state()["playing"] else self.play()
        if action == "skip":
            return self.skip(parsed.value or 10)
        if action == "set_volume":
            return self.set_volume(100 if parsed.value is None else parsed.value)
        if action == "mute":
            return self.set_muted(True)
        if action == "unmute":
            return self.set_muted(False)
        if action == "fullscreen":
            return self._click(".ytp-fullscreen-button", "Fullscreen toggled.")
        if action == "captions":
            return self.set_captions(parsed.enabled)
        if action == "theater":
            return self._click(".ytp-size-button", "Theater mode toggled.")
        if action == "ambient":
            return self.toggle_ambient()
        if action == "autoplay":
            return self.set_autoplay(parsed.enabled)
        if action == "set_speed":
            return self.set_speed(parsed.value or 1)
        if action == "sleep_timer":
            return self.set_sleep_timer(parsed.value or 30)
        if action == "cancel_timer":
            return self.cancel_sleep_timer()
        if action == "next":
            return self._click(".ytp-next-button", "Next video selected.")
        if action == "previous":
            try:
                return self._click(".ytp-prev-button", "Previous video selected.")
            except YouTubeControllerError:
                self._js("history.back();")
                return "Previous YouTube page selected."
        if action == "status":
            state = self.state()
            if not state["launched"]:
                return "YouTube is not open."
            return f"{'Playing' if state['playing'] else 'Paused'}: {state['title'] or 'YouTube video'}."
        if action == "close":
            return self.close()
        if action == "duck":
            return self.duck(parsed.value or 8)
        if action == "restore":
            return self.restore()
        raise YouTubeControllerError(f"Unsupported YouTube action: {action}")


_controller = YouTubeController()


def get_youtube_controller() -> YouTubeController:
    return _controller


def selenium_available() -> bool:
    return _SELENIUM_AVAILABLE
