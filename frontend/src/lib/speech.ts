/**
 * Text-to-speech with the browser's Web Speech API (free, no API calls).
 *
 * `SpeechController` owns the single `speechSynthesis` queue: only one answer speaks at a time,
 * and every player subscribes (Observer) to learn whether it is the one speaking. Voices are
 * ranked so natural/neural voices (Edge "Natural", Google) come first, and the chosen voice is
 * remembered per language. The engine is injected, so the controller is unit-testable.
 */
import { storage } from "./storage";
import { isArabic, sentences, speakable } from "./text";

export type SpeechState = "idle" | "speaking" | "paused";
type Listener = () => void;
type MakeUtterance = (text: string) => SpeechSynthesisUtterance;

const score = (v: SpeechSynthesisVoice) =>
  (/natural|neural/i.test(v.name) ? 3 : 0) +
  (/online|google/i.test(v.name) ? 2 : 0) +
  (v.localService ? 0 : 1);

function browserEngine(): [SpeechSynthesis, MakeUtterance] | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return null;
  if (typeof SpeechSynthesisUtterance === "undefined") return null;
  return [window.speechSynthesis, (text) => new SpeechSynthesisUtterance(text)];
}

export class SpeechController {
  private activeId: string | null = null;
  private state: SpeechState = "idle";
  private readonly listeners = new Set<Listener>();
  private readonly synth: SpeechSynthesis | null;
  private readonly makeUtterance: MakeUtterance | null;

  constructor(engine: [SpeechSynthesis, MakeUtterance] | null = browserEngine()) {
    this.synth = engine?.[0] ?? null;
    this.makeUtterance = engine?.[1] ?? null;
    this.synth?.addEventListener("voiceschanged", () => {
      this.notify();
    });
  }

  get supported(): boolean {
    return this.synth !== null;
  }

  stateOf(id: string): SpeechState {
    return this.activeId === id ? this.state : "idle";
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /** Voices for the answer's language, best first. */
  voicesFor(text: string): SpeechSynthesisVoice[] {
    const lang = languageOf(text);
    const all = this.synth?.getVoices() ?? [];
    const mine = all.filter((v) => v.lang.toLowerCase().startsWith(lang));
    return (mine.length ? mine : all).slice().sort((a, b) => score(b) - score(a));
  }

  preferredVoice(text: string): string | null {
    const saved = storage.get(voiceKey(text));
    const voices = this.voicesFor(text);
    return (voices.find((v) => v.name === saved) ?? voices.at(0))?.name ?? null;
  }

  rememberVoice(text: string, name: string): void {
    storage.set(voiceKey(text), name);
    this.notify();
  }

  speak(id: string, text: string, rate = 1): void {
    const { synth, makeUtterance } = this;
    if (!synth || !makeUtterance) return;
    const clean = speakable(text);
    const parts = sentences(clean);
    if (!parts.length) return;
    synth.cancel();
    const preferred = this.preferredVoice(clean);
    const voice = this.voicesFor(clean).find((v) => v.name === preferred);
    parts.forEach((part, i) => {
      const u = makeUtterance(part);
      if (voice) u.voice = voice;
      u.lang = voice?.lang ?? (isArabic(clean) ? "ar" : "en-US");
      u.rate = rate;
      if (i === parts.length - 1) {
        u.onend = () => {
          if (this.activeId === id) this.set(id, "idle");
        };
      }
      synth.speak(u);
    });
    this.set(id, "speaking");
  }

  /** Play / pause / resume for one answer. */
  toggle(id: string, text: string, rate = 1): void {
    if (this.activeId === id && this.state === "speaking") {
      this.synth?.pause();
      this.set(id, "paused");
    } else if (this.activeId === id && this.state === "paused") {
      this.synth?.resume();
      this.set(id, "speaking");
    } else {
      this.speak(id, text, rate);
    }
  }

  /** Stop speaking; with an id, only if that answer is the one speaking. */
  stop(id?: string): void {
    if (id && this.activeId !== id) return;
    this.synth?.cancel();
    if (this.activeId) this.set(this.activeId, "idle");
  }

  private set(id: string, state: SpeechState): void {
    this.activeId = id;
    this.state = state;
    this.notify();
  }

  private notify(): void {
    this.listeners.forEach((l) => {
      l();
    });
  }
}

function languageOf(text: string): string {
  return isArabic(text) ? "ar" : "en";
}

function voiceKey(text: string): string {
  return `omnicare_voice_${languageOf(text)}`;
}

export const speech = new SpeechController();
