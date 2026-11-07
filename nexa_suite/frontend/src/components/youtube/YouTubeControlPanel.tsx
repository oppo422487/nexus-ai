import { useCallback, useEffect, useState } from "react";
import {
  Captions,
  Gauge,
  Maximize,
  Pause,
  Play,
  RotateCcw,
  RotateCw,
  Search,
  Sparkles,
  SkipBack,
  SkipForward,
  Timer,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import {
  getYouTubeCapabilities,
  getYouTubeStatus,
  requestYouTubeCommand,
  type YouTubePlayerStateDto,
} from "@/lib/backendAssistantClient";

const EMPTY_STATE: YouTubePlayerStateDto = {
  available: false,
  launched: false,
  playing: false,
  muted: false,
  title: "",
  current_time: 0,
  duration: 0,
  volume: 100,
  playback_rate: 1,
  timer_remaining_seconds: null,
  current_url: "",
};

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
}

export function YouTubeControlPanel() {
  const [state, setState] = useState<YouTubePlayerStateDto>(EMPTY_STATE);
  const [query, setQuery] = useState("");
  const [command, setCommand] = useState("");
  const [available, setAvailable] = useState<boolean | null>(null);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Advanced player is checking readiness...");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await getYouTubeStatus();
      if (response.state) setState(response.state);
    } catch {
      setState(EMPTY_STATE);
    }
  }, []);

  useEffect(() => {
    getYouTubeCapabilities()
      .then((response) => {
        setAvailable(response.available);
        setEnabled(response.enabled);
        setMessage(response.message);
      })
      .catch(() => {
        setAvailable(false);
        setEnabled(false);
        setMessage("Start the backend to use advanced YouTube controls.");
      });
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!state.launched) return;
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
  }, [refresh, state.launched]);

  const run = async (input: Parameters<typeof requestYouTubeCommand>[0]) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await requestYouTubeCommand({
        ...input,
        user_confirmed: true,
        source: "dashboard_youtube_panel",
      });
      setMessage(response.message);
      if (response.state) setState(response.state);
      if (!response.executed && response.status !== "ok") {
        setError(response.error ?? response.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "YouTube command failed.");
    } finally {
      setBusy(false);
    }
  };

  const launch = () => {
    void run({ action: "launch", query: query.trim() || null });
  };

  return (
    <section className="nx-card youtube-control-card" aria-label="Advanced YouTube controls">
      <div className="nx-card-head">
        <div className="nx-card-title">
          <span className="youtube-brand-dot" /> Advanced YouTube
        </div>
        <span className={`nx-list-badge ${state.launched ? "ok" : available && enabled ? "mid" : "bad"}`}>
          {state.launched ? (state.playing ? "Playing" : "Paused") : available && enabled ? "Ready" : "Unavailable"}
        </span>
      </div>

      <div className="youtube-now-playing">
        <div>
          <small>Controlled Chrome player</small>
          <strong>{state.title || "No active YouTube video"}</strong>
        </div>
        <span>{formatTime(state.current_time)} / {formatTime(state.duration)}</span>
      </div>

      <div className="youtube-search-row">
        <Search size={16} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search and play a video..."
          onKeyDown={(event) => {
            if (event.key === "Enter") launch();
          }}
        />
        <button type="button" className="nx-btn primary" onClick={launch} disabled={busy || !available || !enabled}>
          <Play size={15} /> Play
        </button>
      </div>

      <div className="youtube-control-grid">
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "previous" })} disabled={busy || !state.launched}><SkipBack size={15} /> Previous</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "skip", value: -10 })} disabled={busy || !state.launched}><RotateCcw size={15} /> 10s</button>
        <button type="button" className="nx-btn primary" onClick={() => void run({ action: state.playing ? "pause" : "resume" })} disabled={busy || !state.launched}>{state.playing ? <Pause size={15} /> : <Play size={15} />}{state.playing ? "Pause" : "Resume"}</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "skip", value: 10 })} disabled={busy || !state.launched}><RotateCw size={15} /> 10s</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "next" })} disabled={busy || !state.launched}><SkipForward size={15} /> Next</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: state.muted ? "unmute" : "mute" })} disabled={busy || !state.launched}>{state.muted ? <Volume2 size={15} /> : <VolumeX size={15} />}{state.muted ? "Unmute" : "Mute"}</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "captions" })} disabled={busy || !state.launched}><Captions size={15} /> Captions</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "fullscreen" })} disabled={busy || !state.launched}><Maximize size={15} /> Fullscreen</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "theater" })} disabled={busy || !state.launched}><Maximize size={15} /> Theater</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "ambient" })} disabled={busy || !state.launched}><Sparkles size={15} /> Ambient</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "autoplay" })} disabled={busy || !state.launched}><RotateCw size={15} /> Autoplay</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "set_speed", value: state.playback_rate >= 2 ? 1 : state.playback_rate + 0.25 })} disabled={busy || !state.launched}><Gauge size={15} /> {state.playback_rate}x</button>
        <button type="button" className="nx-btn ghost" onClick={() => void run({ action: "sleep_timer", value: 30 })} disabled={busy || !state.launched}><Timer size={15} /> 30m</button>
        <button type="button" className="nx-btn ghost danger" onClick={() => void run({ action: "close" })} disabled={busy || !state.launched}><X size={15} /> Close</button>
      </div>

      <div className="youtube-sliders">
        <label>
          <Volume2 size={15} />
          <span>Volume {state.volume}%</span>
          <input
            type="range"
            min="0"
            max="100"
            value={state.volume}
            disabled={busy || !state.launched}
            onChange={(event) => setState((current) => ({ ...current, volume: Number(event.target.value) }))}
            onPointerUp={(event) => void run({ action: "set_volume", value: Number(event.currentTarget.value) })}
          />
        </label>
      </div>

      <div className="youtube-command-row">
        <input
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder='Try “skip forward 20”, “speed 1.5”, or “sleep timer 45”'
          onKeyDown={(event) => {
            if (event.key === "Enter" && command.trim()) {
              void run({ action: "auto", command: command.trim() });
              setCommand("");
            }
          }}
        />
        <button
          type="button"
          className="nx-btn ghost"
          disabled={busy || !command.trim() || !available || !enabled}
          onClick={() => {
            void run({ action: "auto", command: command.trim() });
            setCommand("");
          }}
        >
          Run command
        </button>
      </div>

      <p className="youtube-control-message">{busy ? "Applying YouTube command..." : message}</p>
      {state.timer_remaining_seconds != null && state.timer_remaining_seconds > 0 && (
        <p className="youtube-timer-message">Sleep timer: {Math.ceil(state.timer_remaining_seconds / 60)} minute(s) remaining</p>
      )}
      {error && <div className="nx-result-err">{error}</div>}
    </section>
  );
}
