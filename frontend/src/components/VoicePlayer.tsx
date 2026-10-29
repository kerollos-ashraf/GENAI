import { useSpeechState, useVoiceVersion } from "../hooks/useSpeech";
import { speech } from "../lib/speech";
import { speakable } from "../lib/text";
import { Icon } from "./Icon";
import "./VoicePlayer.css";

const LABELS = { idle: "Listen", speaking: "Speaking…", paused: "Paused" } as const;

/** Play / pause / stop an answer aloud, with a voice picker (Web Speech API, free). */
export function VoicePlayer({ id, text, rate }: { id: string; text: string; rate: number }) {
  const state = useSpeechState(id);
  useVoiceVersion();
  if (!speech.supported) return null;

  const clean = speakable(text);
  const voices = speech.voicesFor(clean);
  const selected = speech.preferredVoice(clean) ?? "";

  return (
    <div className={`player ${state}`} data-testid="voice-player">
      <button
        className="play"
        onClick={() => {
          speech.toggle(id, text, rate);
        }}
        aria-label={state === "speaking" ? "Pause" : "Play answer"}
      >
        <Icon name={state === "speaking" ? "pause" : "play"} size={14} />
      </button>
      <button
        className="stop"
        onClick={() => {
          speech.stop(id);
        }}
        aria-label="Stop"
      >
        <Icon name="stop" size={12} />
      </button>
      <span className="wave" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
        <i />
      </span>
      <span className="label">{LABELS[state]}</span>
      {voices.length > 0 && (
        <select
          aria-label="Voice"
          value={selected}
          onChange={(e) => {
            speech.rememberVoice(clean, e.target.value);
          }}
        >
          {voices.map((v) => (
            <option key={v.name} value={v.name}>
              {v.name.replace(/^Microsoft /, "").replace(/ - .*$/, "")}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
