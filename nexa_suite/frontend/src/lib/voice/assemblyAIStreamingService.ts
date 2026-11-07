import type { RecognitionHandlers } from "./recognitionService";

type AssemblyMessage = {
  type?: "Begin" | "Turn" | "Termination" | "Error";
  transcript?: string;
  end_of_turn?: boolean;
  error?: string;
};

function pcm16(input: Float32Array): ArrayBuffer {
  const output = new Int16Array(input.length);
  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[index]));
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output.buffer;
}

export class AssemblyAIStreamingService {
  private socket: WebSocket | null = null;
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private stopped = true;

  async start(handlers: RecognitionHandlers): Promise<void> {
    this.stop();
    const tokenResponse = await fetch("http://127.0.0.1:8766/api/voice/stt/assemblyai/token");
    if (!tokenResponse.ok) throw new Error(`AssemblyAI token request failed (${tokenResponse.status}).`);
    const tokenPayload = await tokenResponse.json() as { ok?: boolean; token?: string; message?: string };
    if (!tokenPayload.ok || !tokenPayload.token) throw new Error(tokenPayload.message || "AssemblyAI streaming is unavailable.");

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.context = new AudioContext();
    await this.context.resume();
    const sampleRate = this.context.sampleRate;
    this.source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    const silentGain = this.context.createGain();
    silentGain.gain.value = 0;

    const params = new URLSearchParams({
      sample_rate: String(sampleRate),
      speech_model: "whisper-rt",
      language_detection: "true",
      format_turns: "true",
      token: tokenPayload.token,
    });
    const socket = new WebSocket(`wss://streaming.assemblyai.com/v3/ws?${params}`);
    socket.binaryType = "arraybuffer";
    this.socket = socket;
    this.stopped = false;

    await new Promise<void>((resolve, reject) => {
      let ready = false;
      const timeout = window.setTimeout(() => reject(new Error("AssemblyAI connection timed out.")), 12_000);
      socket.onmessage = (event) => {
        const message = JSON.parse(String(event.data)) as AssemblyMessage;
        if (message.type === "Begin") {
          ready = true;
          window.clearTimeout(timeout);
          handlers.onStart?.();
          resolve();
        } else if (message.type === "Turn" && message.transcript?.trim()) {
          if (message.end_of_turn) handlers.onFinal?.(message.transcript.trim());
          else handlers.onInterim?.(message.transcript.trim());
        } else if (message.type === "Error") {
          const detail = message.error || "AssemblyAI streaming failed.";
          if (ready) handlers.onError?.("network", detail);
          else reject(new Error(detail));
        }
      };
      socket.onerror = () => {
        window.clearTimeout(timeout);
        if (!ready) reject(new Error("AssemblyAI streaming connection failed."));
        else handlers.onError?.("network", "AssemblyAI streaming connection was interrupted.");
      };
      socket.onclose = (event) => {
        window.clearTimeout(timeout);
        if (!this.stopped && ready && event.code !== 1000) handlers.onError?.("network", event.reason || "AssemblyAI streaming connection closed.");
      };
    });

    this.processor.onaudioprocess = (event) => {
      if (this.stopped || socket.readyState !== WebSocket.OPEN) return;
      socket.send(pcm16(event.inputBuffer.getChannelData(0)));
    };
    this.source.connect(this.processor);
    this.processor.connect(silentGain);
    silentGain.connect(this.context.destination);
  }

  stop(): void {
    this.stopped = true;
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: "Terminate" }));
    if (this.processor) { this.processor.disconnect(); this.processor.onaudioprocess = null; }
    this.source?.disconnect();
    this.stream?.getTracks().forEach((track) => track.stop());
    void this.context?.close();
    if (this.socket && this.socket.readyState < WebSocket.CLOSING) this.socket.close(1000, "client stopped");
    this.socket = null; this.stream = null; this.context = null; this.processor = null; this.source = null;
  }
}
