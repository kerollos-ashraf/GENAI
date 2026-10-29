/** Microphone recording with MediaRecorder. `finish()` resolves with the recording. */
import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderStatus = "idle" | "recording";

export interface Recording {
  audio: Blob;
  filename: string;
}

const EXTENSIONS: Record<string, string> = {
  webm: "webm",
  ogg: "ogg",
  mp4: "m4a",
  mpeg: "mp3",
  wav: "wav",
};

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return ["audio/webm;codecs=opus", "audio/webm", "audio/ogg", "audio/mp4"].find((t) =>
    MediaRecorder.isTypeSupported(t),
  );
}

export function filenameFor(mimeType: string): string {
  const subtype = mimeType.split("/")[1]?.split(";")[0] ?? "webm";
  return `question.${EXTENSIONS[subtype] ?? "webm"}`;
}

/** Microphone recording needs getUserMedia and MediaRecorder (missing on old browsers / http). */
function canRecord(): boolean {
  return "mediaDevices" in navigator && typeof MediaRecorder !== "undefined";
}

export function useRecorder() {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<number | undefined>(undefined);

  const supported = canRecord();

  const cleanup = useCallback(() => {
    window.clearInterval(timer.current);
    recorder.current?.stream.getTracks().forEach((t) => {
      t.stop();
    });
    recorder.current = null;
    setStatus("idle");
    setSeconds(0);
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: pickMimeType() });
      chunks.current = [];
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      rec.start(250);
      recorder.current = rec;
      setStatus("recording");
      const began = Date.now();
      timer.current = window.setInterval(() => {
        setSeconds(Math.floor((Date.now() - began) / 1000));
      }, 250);
    } catch {
      setError("Microphone unavailable. Allow microphone access in your browser and try again.");
      cleanup();
    }
  }, [cleanup]);

  const finish = useCallback(
    () =>
      new Promise<Recording | null>((resolve) => {
        const rec = recorder.current;
        if (!rec) {
          resolve(null);
          return;
        }
        rec.onstop = () => {
          const type = rec.mimeType || "audio/webm";
          const audio = new Blob(chunks.current, { type });
          cleanup();
          resolve(audio.size ? { audio, filename: filenameFor(type) } : null);
        };
        rec.stop();
      }),
    [cleanup],
  );

  const cancel = useCallback(() => {
    if (recorder.current) {
      recorder.current.onstop = null;
      recorder.current.stop();
    }
    cleanup();
  }, [cleanup]);

  return { supported, status, seconds, error, start, finish, cancel };
}
