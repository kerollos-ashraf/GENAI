import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";

const NEAR_BOTTOM_PX = 120;
const SMOOTH_SCROLL_MAX_MS = 900;

/**
 * Keeps a scroll container pinned to the newest message - but only while the reader is at the
 * bottom. Someone who scrolled up to reread an answer isn't yanked down; they get `showJump`.
 *
 * Our own smooth scrolling also fires scroll events (from positions far above the bottom), so
 * while it runs those events are ignored; otherwise the view would unpin itself.
 */
export function useAutoScroll(container: RefObject<HTMLElement | null>, changeKey: unknown) {
  const [atBottom, setAtBottom] = useState(true);
  const pinned = useRef(true);
  const autoScrolling = useRef(false);
  const settle = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(settle.current), []);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const el = container.current;
      if (!el) return;
      pinned.current = true;
      setAtBottom(true);
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      if (behavior === "smooth" && distance > 1) {
        // Ends when we arrive (see onScroll), on user input, or after the animation at most.
        autoScrolling.current = true;
        window.clearTimeout(settle.current);
        settle.current = window.setTimeout(() => {
          autoScrolling.current = false;
        }, SMOOTH_SCROLL_MAX_MS);
      }
      el.scrollTo({ top: el.scrollHeight, behavior });
    },
    [container],
  );

  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const onScroll = () => {
      const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
      if (autoScrolling.current) {
        if (near) autoScrolling.current = false; // arrived
        return;
      }
      pinned.current = near;
      setAtBottom(near);
    };
    // A wheel, touch or key press means the person is scrolling, even mid-animation.
    const onUserScroll = () => {
      autoScrolling.current = false;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    el.addEventListener("wheel", onUserScroll, { passive: true });
    el.addEventListener("touchstart", onUserScroll, { passive: true });
    el.addEventListener("keydown", onUserScroll);
    return () => {
      el.removeEventListener("scroll", onScroll);
      el.removeEventListener("wheel", onUserScroll);
      el.removeEventListener("touchstart", onUserScroll);
      el.removeEventListener("keydown", onUserScroll);
    };
  }, [container]);

  useLayoutEffect(() => {
    if (pinned.current) scrollToBottom();
  }, [changeKey, scrollToBottom]);

  return { showJump: !atBottom, scrollToBottom };
}
