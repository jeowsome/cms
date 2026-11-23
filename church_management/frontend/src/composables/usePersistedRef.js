import { ref, watch } from "vue";

/**
 * A ref mirrored to localStorage ("local", survives restarts) or
 * sessionStorage ("session", survives navigating away and back in the tab).
 * Storage can be blocked (private mode), so every access is guarded and the
 * ref still works in memory.
 */
export function usePersistedRef(key, fallback, kind = "local") {
  const store = () => (kind === "session" ? window.sessionStorage : window.localStorage);
  let initial = fallback;
  try {
    const raw = store().getItem(key);
    if (raw !== null) initial = JSON.parse(raw);
  } catch {}
  const value = ref(initial);
  watch(value, (v) => {
    try {
      if (v === null || v === undefined) store().removeItem(key);
      else store().setItem(key, JSON.stringify(v));
    } catch {}
  });
  return value;
}
