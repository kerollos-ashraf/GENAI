import { useSyncExternalStore } from "react";
import { speech, type SpeechState } from "../lib/speech";

/** This answer's playback state; re-renders when any player starts, stops or voices load. */
export function useSpeechState(id: string): SpeechState {
  return useSyncExternalStore(
    (listener) => speech.subscribe(listener),
    () => speech.stateOf(id),
  );
}

/** Bumps when voices load, so voice pickers refresh. */
export function useVoiceVersion(): number {
  return useSyncExternalStore(
    (listener) => speech.subscribe(listener),
    () => speech.voicesFor("").length,
  );
}
