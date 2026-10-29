import { useCallback, useEffect, useState } from "react";
import { DEFAULT_USER_ID } from "../config";
import { storage } from "../lib/storage";
import type { ReplyMode, Theme } from "../types";

/** Storage keys. `THEME_KEY` is also read by the inline script in index.html (no flash). */
export const THEME_KEY = "omnicare_theme";

function useStored<T extends string | number>(key: string, initial: T, parse: (raw: string) => T) {
  const [value, setValue] = useState<T>(() => {
    const raw = storage.get(key);
    return raw === null ? initial : parse(raw);
  });
  const update = useCallback(
    (next: T) => {
      setValue(next);
      storage.set(key, String(next));
    },
    [key],
  );
  return [value, update] as const;
}

const oneOf =
  <T extends string>(allowed: readonly T[], fallback: T) =>
  (raw: string): T =>
    (allowed as readonly string[]).includes(raw) ? (raw as T) : fallback;

/** Applies the theme to <html>; "system" follows the operating system. */
function useApplyTheme(theme: Theme) {
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") delete root.dataset.theme;
    else root.dataset.theme = theme;
  }, [theme]);
}

/** User id, spoken-reply mode, speaking speed and theme, remembered in this browser. */
export function usePreferences() {
  const [userId, setUserId] = useStored("omnicare_user_id", DEFAULT_USER_ID, (r) => r);
  const [replyMode, setReplyMode] = useStored<ReplyMode>(
    "omnicare_reply_mode",
    "auto",
    oneOf<ReplyMode>(["auto", "always", "off"], "auto"),
  );
  const [rate, setRate] = useStored("omnicare_rate", 1, (r) => {
    const n = Number(r);
    return n >= 0.7 && n <= 1.5 ? n : 1;
  });
  const [theme, setTheme] = useStored<Theme>(
    THEME_KEY,
    "system",
    oneOf<Theme>(["system", "light", "dark"], "system"),
  );
  useApplyTheme(theme);

  return { userId, setUserId, replyMode, setReplyMode, rate, setRate, theme, setTheme };
}

export type Preferences = ReturnType<typeof usePreferences>;
