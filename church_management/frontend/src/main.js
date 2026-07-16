import { createApp } from "vue";
import { createPinia } from "pinia";
import { PiniaColada } from "@pinia/colada";
import App from "./App.vue";
import router from "./router";
import "./assets/style.css";

// A long-running SPA tab holds an index.js whose lazy chunks get deleted by
// the next `npm run build` (emptyOutDir). When such a chunk 404s, reload the
// page so the browser picks up the current bundle — otherwise navigation
// silently aborts and the user is stuck (e.g. frozen on "Redirecting…").
// Reload at most once: a persistent failure (poisoned cache, blocked request)
// must surface as an error instead of an infinite reload loop.
window.addEventListener("vite:preloadError", (event) => {
  if (sessionStorage.getItem("cm-preload-reload")) return;
  sessionStorage.setItem("cm-preload-reload", "1");
  event.preventDefault();
  window.location.reload();
});

const app = createApp(App);

const pinia = createPinia();
app.use(pinia);
app.use(PiniaColada);
app.use(router);

app.mount("#app");
