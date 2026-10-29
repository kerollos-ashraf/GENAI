import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { MAX_MESSAGE_CHARS } from "../config";
import { useRecorder } from "../hooks/useRecorder";
import "./Composer.css";
import { Icon } from "./Icon";

interface Props {
  busy: boolean;
  onSend: (text: string) => void;
  onVoice: (audio: Blob, filename: string) => void;
  notice: string | null;
}

const COUNTER_FROM = MAX_MESSAGE_CHARS - 200;

/** Text box with send, plus a mic that records, then sends or cancels the recording. */
export function Composer({ busy, onSend, onVoice, notice }: Props) {
  const [text, setText] = useState("");
  const recorder = useRecorder();
  const input = useRef<HTMLTextAreaElement>(null);
  const recording = recorder.status === "recording";
  const canSend = text.trim().length > 0 && !busy;

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!canSend) return;
    onSend(text);
    setText("");
    input.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const sendRecording = async () => {
    const result = await recorder.finish();
    if (result) onVoice(result.audio, result.filename);
  };

  const message = recorder.error ?? notice;

  return (
    <div className="composer-wrap">
      {message && (
        <p className="notice" role="alert">
          <Icon name="alert" size={15} /> {message}
        </p>
      )}
      <form className={`composer${recording ? " recording" : ""}`} onSubmit={submit}>
        {recording ? (
          <div className="recording-bar" role="status">
            <span className="rec-dot" aria-hidden="true" />
            Listening… {formatClock(recorder.seconds)}
          </div>
        ) : (
          <textarea
            ref={input}
            data-testid="composer-input"
            rows={1}
            value={text}
            maxLength={MAX_MESSAGE_CHARS}
            placeholder="Ask about your coverage or a claim…"
            aria-label="Your question"
            aria-describedby="composer-hint"
            onChange={(e) => {
              setText(e.target.value);
            }}
            onKeyDown={onKeyDown}
          />
        )}
        {recording ? (
          <>
            <button
              type="button"
              className="icon-button"
              onClick={recorder.cancel}
              aria-label="Cancel recording"
            >
              <Icon name="close" />
            </button>
            <button
              type="button"
              className="send"
              onClick={() => void sendRecording()}
              aria-label="Send recording"
            >
              <Icon name="check" />
            </button>
          </>
        ) : (
          <>
            {recorder.supported && (
              <button
                type="button"
                className="icon-button"
                onClick={() => void recorder.start()}
                disabled={busy}
                aria-label="Ask by voice"
              >
                <Icon name="mic" />
              </button>
            )}
            <button type="submit" className="send" disabled={!canSend} aria-label="Send question">
              <Icon name="send" />
            </button>
          </>
        )}
      </form>
      <p className="composer-hint" id="composer-hint">
        <span>Enter to send, Shift+Enter for a new line</span>
        {text.length >= COUNTER_FROM && (
          <span className="counter">
            {text.length.toLocaleString()} / {MAX_MESSAGE_CHARS.toLocaleString()}
          </span>
        )}
      </p>
    </div>
  );
}

function formatClock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
