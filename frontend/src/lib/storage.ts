/** Per-browser preferences. Storage can be unavailable (private mode, blocked site data), so
 * every access is guarded and callers always get a usable default. */
export const storage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* preference just isn't remembered */
    }
  },
};
