/**
 * Frappe socket.io realtime client. Connects once and shares the connection.
 *
 * Frappe v15 publishes realtime events on the same host at /socket.io/. Auth is
 * cookie-based (same session as the page), so we just connect with credentials.
 */
import { io } from "socket.io-client";
import { onBeforeUnmount } from "vue";

let socket = null;

function getSocket() {
  if (socket) return socket;
  const url = window.location.origin;
  socket = io(url, {
    withCredentials: true,
    transports: ["websocket", "polling"],
    path: "/socket.io",
  });
  socket.on("connect", () => {
    // Frappe room subscription pattern — we only need broadcast events here.
  });
  return socket;
}

/**
 * Subscribe to a Frappe realtime event for the lifetime of the calling component.
 * Returns the unsubscribe function in case manual control is needed.
 */
export function useRealtime(event, handler) {
  const s = getSocket();
  s.on(event, handler);
  const off = () => s.off(event, handler);
  onBeforeUnmount(off);
  return off;
}

export function useSocket() {
  return getSocket();
}
