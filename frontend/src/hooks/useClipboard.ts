import { useCallback, useEffect, useRef, useState } from "react";

/** Copy text; `copied` is true for a moment afterwards so the button can confirm it. */
export function useClipboard(resetAfterMs = 1800) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = useCallback(
    async (text: string) => {
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        return false; // no permission or insecure context: the button simply doesn't confirm
      }
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        setCopied(false);
      }, resetAfterMs);
      return true;
    },
    [resetAfterMs],
  );

  return { copied, copy };
}
