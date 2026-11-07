/**
 * Microphone recorders for push-to-talk and continuous voice activity.
 *
 * Audio is encoded as 16 kHz mono WAV for backend transcription. Continuous
 * mode keeps one stream open but uploads only locally detected utterances.
 */

export type PushToTalkRecorder = {
  stop: () => Promise<Blob>;
  cancel: () => void;
};

export type ContinuousVoiceCapture = {
  stop: () => void;
  setPaused: (paused: boolean) => void;
};

export type ContinuousVoiceCaptureOptions = {
  onUtterance: (audio: Blob) => void | Promise<void>;
  onVoiceState?: (hearingVoice: boolean) => void;
  onAudioLevel?: (level: number) => void;
  onError?: (error: Error) => void;
};

const TARGET_SAMPLE_RATE = 16000;
const MAX_RECORDING_SECONDS = 60;
const VAD_THRESHOLD = 0.014;
const VAD_SILENCE_MS = 900;
const VAD_MIN_VOICE_MS = 280;
const VAD_MAX_UTTERANCE_MS = 14_000;
const VAD_PRE_ROLL_MS = 320;

function downsampleBuffer(
  buffer: Float32Array,
  inputRate: number,
  targetRate: number,
): Float32Array {
  if (targetRate >= inputRate) return buffer;
  const ratio = inputRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), buffer.length);
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      sum += buffer[j];
      count++;
    }
    result[i] = count > 0 ? sum / count : 0;
  }
  return result;
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

export async function startPushToTalkRecording(): Promise<PushToTalkRecorder> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone capture is not supported in this environment.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
    },
  });

  const audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  let totalSamples = 0;
  let stopped = false;

  processor.onaudioprocess = (event) => {
    if (stopped) return;
    const input = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(input));
    totalSamples += input.length;
    if (totalSamples / audioContext.sampleRate > MAX_RECORDING_SECONDS) {
      stopped = true;
    }
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  const releaseAll = () => {
    stopped = true;
    try {
      processor.disconnect();
      source.disconnect();
    } catch {
      // already disconnected
    }
    stream.getTracks().forEach((track) => track.stop());
    void audioContext.close();
  };

  return {
    stop: async () => {
      releaseAll();
      const merged = new Float32Array(totalSamples);
      let offset = 0;
      for (const chunk of chunks) {
        merged.set(chunk, offset);
        offset += chunk.length;
      }
      const downsampled = downsampleBuffer(
        merged,
        audioContext.sampleRate,
        TARGET_SAMPLE_RATE,
      );
      return encodeWav(downsampled, TARGET_SAMPLE_RATE);
    },
    cancel: () => {
      releaseAll();
    },
  };
}

/** Keep one mic stream alive and emit utterance-sized WAV files after silence. */
export async function startContinuousVoiceCapture(
  options: ContinuousVoiceCaptureOptions,
): Promise<ContinuousVoiceCapture> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone capture is not supported in this environment.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
  const audioContext = new AudioContext();
  await audioContext.resume();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(2048, 1, 1);
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;
  source.connect(processor);
  processor.connect(silentGain);
  silentGain.connect(audioContext.destination);

  const samplesPerMs = audioContext.sampleRate / 1000;
  const preRollLimit = Math.ceil(VAD_PRE_ROLL_MS * samplesPerMs);
  let preRoll: Float32Array[] = [];
  let preRollSamples = 0;
  let utterance: Float32Array[] = [];
  let utteranceSamples = 0;
  let voicedSamples = 0;
  let silentSamples = 0;
  let active = false;
  let externallyPaused = false;
  let stopped = false;
  let delivering = false;
  let lastLevelAt = 0;

  const resetUtterance = () => {
    utterance = [];
    utteranceSamples = 0;
    voicedSamples = 0;
    silentSamples = 0;
    if (active) options.onVoiceState?.(false);
    active = false;
  };

  const deliver = () => {
    if (delivering || voicedSamples < VAD_MIN_VOICE_MS * samplesPerMs) {
      resetUtterance();
      return;
    }
    const chunks = utterance;
    const total = utteranceSamples;
    resetUtterance();
    delivering = true;
    const merged = new Float32Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    const downsampled = downsampleBuffer(merged, audioContext.sampleRate, TARGET_SAMPLE_RATE);
    void Promise.resolve(options.onUtterance(encodeWav(downsampled, TARGET_SAMPLE_RATE)))
      .catch((error) => options.onError?.(error instanceof Error ? error : new Error("Voice processing failed.")))
      .finally(() => {
        delivering = false;
      });
  };

  processor.onaudioprocess = (event) => {
    if (stopped || externallyPaused || delivering) return;
    const input = new Float32Array(event.inputBuffer.getChannelData(0));
    let energy = 0;
    for (let index = 0; index < input.length; index += 1) energy += input[index] * input[index];
    const rms = Math.sqrt(energy / Math.max(1, input.length));
    const now = performance.now();
    if (now - lastLevelAt >= 100) {
      lastLevelAt = now;
      options.onAudioLevel?.(Math.max(0, Math.min(1, rms * 24)));
    }
    const voice = rms >= VAD_THRESHOLD;

    if (!active) {
      preRoll.push(input);
      preRollSamples += input.length;
      while (preRollSamples > preRollLimit && preRoll.length > 1) {
        preRollSamples -= preRoll[0].length;
        preRoll.shift();
      }
      if (!voice) return;
      active = true;
      options.onVoiceState?.(true);
      utterance = [...preRoll];
      utteranceSamples = preRollSamples;
      preRoll = [];
      preRollSamples = 0;
    } else {
      utterance.push(input);
      utteranceSamples += input.length;
    }

    if (voice) {
      voicedSamples += input.length;
      silentSamples = 0;
    } else {
      silentSamples += input.length;
    }

    if (
      silentSamples >= VAD_SILENCE_MS * samplesPerMs ||
      utteranceSamples >= VAD_MAX_UTTERANCE_MS * samplesPerMs
    ) deliver();
  };

  const release = () => {
    if (stopped) return;
    stopped = true;
    resetUtterance();
    try {
      processor.disconnect();
      silentGain.disconnect();
      source.disconnect();
    } catch {
      // already disconnected
    }
    stream.getTracks().forEach((track) => track.stop());
    void audioContext.close();
  };

  return {
    stop: release,
    setPaused: (nextPaused) => {
      externallyPaused = nextPaused;
      if (externallyPaused) resetUtterance();
    },
  };
}
