import type { IconName } from "./components/Icon";
import type { ReplyMode, Theme } from "./types";

export interface Suggestion {
  label: string;
  question: string;
  icon: IconName;
}

/** Tap-to-ask suggestions on an empty chat. */
export const SUGGESTIONS: readonly Suggestion[] = [
  {
    label: "Is a burst pipe covered?",
    question: "Is water damage from a burst pipe covered?",
    icon: "drop",
  },
  { label: "Are floods covered?", question: "Are floods covered?", icon: "umbrella" },
  {
    label: "Check claim CLM-8821",
    question: "What's the status of claim CLM-8821?",
    icon: "search",
  },
  {
    label: "File a water damage claim",
    question:
      "I want to file a claim: policy POL-1092, water damage, $4,200, kitchen pipe burst overnight.",
    icon: "doc",
  },
];

export interface Choice<T> {
  value: T;
  label: string;
  icon?: IconName;
}

export const REPLY_MODES: readonly Choice<ReplyMode>[] = [
  { value: "auto", label: "When I ask by voice" },
  { value: "always", label: "Always" },
  { value: "off", label: "Never" },
];

export const THEMES: readonly Choice<Theme>[] = [
  { value: "system", label: "System", icon: "monitor" },
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
];

export const DOCUMENT_TYPES = [".md", ".markdown", ".txt", ".pdf"];

export const DEFAULT_USER_ID = "usr_123";
export const USER_ID_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;
export const MAX_MESSAGE_CHARS = 2000;
export const HEALTH_POLL_MS = 15_000;
