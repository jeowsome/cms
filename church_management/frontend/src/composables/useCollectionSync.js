/**
 * Live, multi-device editing for a Collection draft.
 *
 * Every edit autosaves on its own — one entry row, one tally row or one header
 * field at a time — after a short debounce. The server broadcasts each change
 * to everyone viewing the same collection (socket.io doc room), and incoming
 * changes are merged into the local form without touching anything this tab
 * is still editing. Nothing is ever wholesale-overwritten, so switching
 * browser tabs or reconnecting can no longer wipe typed input.
 *
 * Local rows carry `_key` (stable client id for v-for) and `name` (server row
 * id, null until the row's first save).
 */
import { onBeforeUnmount, reactive, ref, watch } from "vue";
import { call } from "@/composables/useFrappeApi";
import { useSocket } from "@/composables/useRealtime";

const API = "church_management.api.collection.";
const SYNC_EVENT_NAME = "collection_sync";
const DEBOUNCE_MS = 450;
const RETRY_MS = 3000;

export const ENTRY_TABLES = ["tithes_collection", "offering_collection", "mission_collection"];
const NUMBER_FIELDS = [
  "benevolence_collection",
  "benevolence_collection_cls",
  "loose_collection",
  "loose_collection_cls",
  "sunday_school_collection",
];
const HEADER_FIELDS = ["date", "cost_center", "attendees", ...NUMBER_FIELDS];

let keySeq = 0;
export function newRowKey() {
  return `r${++keySeq}`;
}

export function blankRow() {
  return { _key: newRowKey(), name: null, number: "", first_name: "", last_name: "", amount: null, account_type: "Cash" };
}

export function useCollectionSync({ form, lookupMember, onCreated, onDeleted, onError }) {
  const clientId = (crypto.randomUUID && crypto.randomUUID()) || Math.random().toString(36).slice(2);
  const socket = useSocket();

  // Keys with a scheduled or in-flight save: "f:<field>", "t:<denum>", "r:<_key>".
  // Remote updates never overwrite these — the local edit is about to win.
  const pendingKeys = reactive(new Set());
  const timers = new Map(); // key -> { id, task }
  const chains = new Map(); // key -> promise of the last queued task
  const connected = ref(socket.connected);
  const viewers = ref([]);
  const offline = ref(false);
  // Rows this tab deleted — a resync fetched before the delete committed must not resurrect them
  const deletedNames = new Set();

  // -------------------------------------------------------------------------
  // Creating the draft on the first edit of a new collection
  // -------------------------------------------------------------------------
  let creating = null;
  function ensureDoc() {
    if (form.name) return Promise.resolve(form.name);
    if (!creating) {
      creating = call(API + "create_draft", {
        doc: {
          date: form.date,
          cost_center: form.cost_center || null,
          collection_tally: form.collection_tally.map((r) => ({
            denum_name: r.denum_name,
            denomination: r.denomination,
            quantity: 0,
            quantity_coins: 0,
            total: 0,
          })),
        },
        client_id: clientId,
      })
        .then((doc) => {
          merge(doc);
          onCreated?.(doc);
          return doc.name;
        })
        .finally(() => {
          creating = null;
        });
    }
    return creating;
  }

  // -------------------------------------------------------------------------
  // Debounced, per-key serialized saves
  // -------------------------------------------------------------------------
  function schedule(key, task, delay = DEBOUNCE_MS) {
    pendingKeys.add(key);
    clearTimeout(timers.get(key)?.id);
    timers.set(key, { id: setTimeout(() => run(key, task), delay), task });
  }

  function run(key, task) {
    timers.delete(key);
    const prev = chains.get(key) || Promise.resolve();
    const p = prev
      .then(() => ensureDoc())
      .then(task)
      .then(() => {
        offline.value = false;
      })
      .catch((e) => {
        if (!e.status) {
          // Network failure — keep the edit and retry until it goes through
          offline.value = true;
          schedule(key, task, RETRY_MS);
        } else {
          onError?.(e);
        }
      })
      .finally(() => {
        if (chains.get(key) === p) {
          chains.delete(key);
          if (!timers.has(key)) pendingKeys.delete(key);
        }
      });
    chains.set(key, p);
    return p;
  }

  /** Send everything scheduled now and wait until all saves have finished. */
  async function flush() {
    for (const [key, { id, task }] of [...timers]) {
      clearTimeout(id);
      run(key, task);
    }
    while (chains.size) await Promise.all([...chains.values()]);
  }

  function cancelAll() {
    for (const { id } of timers.values()) clearTimeout(id);
    timers.clear();
    pendingKeys.clear();
  }

  // -------------------------------------------------------------------------
  // Local edits → server
  // -------------------------------------------------------------------------
  function touchField(field) {
    schedule(`f:${field}`, () =>
      call(API + "set_fields", { name: form.name, values: { [field]: form[field] }, client_id: clientId })
    );
  }

  function touchTally(row) {
    schedule(`t:${row.denum_name}`, () =>
      call(API + "set_tally", {
        name: form.name,
        denum_name: row.denum_name,
        quantity: row.quantity || 0,
        quantity_coins: row.quantity_coins || 0,
        client_id: clientId,
      })
    );
  }

  function touchRow(table, row) {
    schedule(`r:${row._key}`, async () => {
      if (row._removed || (!row.number && !row.amount)) {
        // Removed or emptied — drop it server-side, keep any local blank row
        if (row.name) {
          const rowName = row.name;
          row.name = null;
          deletedNames.add(rowName);
          await call(API + "delete_row", { name: form.name, table, row_name: rowName, client_id: clientId });
        }
        return;
      }
      const member = row.number ? lookupMember(row.number) : null;
      if (row.number && !member) return; // unknown envelope — saved once it resolves
      const saved = await call(API + "upsert_row", {
        name: form.name,
        table,
        row: { name: row.name, number: member ? member.name : "", amount: row.amount || 0, account_type: row.account_type || "Cash" },
        client_id: clientId,
      });
      row.name = saved.name;
      // A resync that landed mid-save may already have added this row as "remote"
      const rows = form[table];
      for (let i = rows.length - 1; i >= 0; i--) {
        if (rows[i] !== row && rows[i].name === saved.name) rows.splice(i, 1);
      }
    });
  }

  function removeRow(table, row) {
    row._removed = true;
    touchRow(table, row);
  }

  // -------------------------------------------------------------------------
  // Server → local merge (never overwrites pending local edits)
  // -------------------------------------------------------------------------
  function headerValue(field, v) {
    if (field === "attendees") return v ?? null;
    if (NUMBER_FIELDS.includes(field)) return v || 0;
    return v || "";
  }

  function assignRow(local, remote) {
    local.name = remote.name;
    local.number = remote.number || "";
    local.first_name = remote.first_name || "";
    local.last_name = remote.last_name || "";
    local.amount = remote.amount ?? null;
    local.account_type = remote.account_type || "Cash";
  }

  // Remote rows go before this tab's trailing unsaved rows, so the row being
  // typed in stays last and the Tab-to-next-row flow keeps working.
  function insertRemoteRow(rows, remote) {
    const row = { _key: newRowKey() };
    assignRow(row, remote);
    let at = rows.length;
    while (at > 0 && !rows[at - 1].name) at--;
    rows.splice(at, 0, row);
  }

  function applyRow(table, remote) {
    const rows = form[table];
    if (!rows || deletedNames.has(remote.name)) return;
    const local = rows.find((r) => r.name === remote.name);
    if (!local) insertRemoteRow(rows, remote);
    else if (!pendingKeys.has(`r:${local._key}`)) assignRow(local, remote);
  }

  function applyRowDelete(table, rowName) {
    const rows = form[table];
    const i = rows ? rows.findIndex((r) => r.name === rowName) : -1;
    if (i === -1) return;
    if (pendingKeys.has(`r:${rows[i]._key}`)) return; // still being edited here — it will be re-created
    rows.splice(i, 1);
  }

  function applyTally(remote) {
    if (pendingKeys.has(`t:${remote.denum_name}`)) return;
    const local = form.collection_tally.find((r) => r.denum_name === remote.denum_name);
    const values = {
      denum_name: remote.denum_name,
      denomination: remote.denomination,
      quantity: remote.quantity || 0,
      quantity_coins: remote.quantity_coins || 0,
      total: remote.total || 0,
    };
    if (local) Object.assign(local, values);
    else form.collection_tally.push(values);
  }

  function merge(doc) {
    form.name = doc.name;
    form.docstatus = doc.docstatus;
    form.journal_entry = doc.journal_entry || null;
    for (const f of HEADER_FIELDS) {
      if (!pendingKeys.has(`f:${f}`)) form[f] = headerValue(f, doc[f]);
    }
    for (const table of ENTRY_TABLES) {
      const remote = doc[table] || [];
      const names = new Set(remote.map((r) => r.name));
      const rows = form[table];
      for (let i = rows.length - 1; i >= 0; i--) {
        const r = rows[i];
        if (r.name && !names.has(r.name) && !pendingKeys.has(`r:${r._key}`)) rows.splice(i, 1);
      }
      for (const r of remote) applyRow(table, r);
    }
    for (const r of doc.collection_tally || []) applyTally(r);
  }

  async function resync() {
    if (!form.name) return;
    try {
      merge(await call(API + "get_detail", { name: form.name }));
    } catch (e) {
      if (e.status === 404) onDeleted?.();
    }
  }

  // -------------------------------------------------------------------------
  // Realtime wiring
  // -------------------------------------------------------------------------
  function onSync(msg) {
    if (!msg || msg.name !== form.name || msg.client_id === clientId) return;
    switch (msg.op) {
      case "row":
        applyRow(msg.table, msg.row);
        break;
      case "row_delete":
        applyRowDelete(msg.table, msg.row_name);
        break;
      case "fields":
        for (const [k, v] of Object.entries(msg.values || {})) {
          if (HEADER_FIELDS.includes(k) && !pendingKeys.has(`f:${k}`)) form[k] = headerValue(k, v);
        }
        break;
      case "tally":
        applyTally(msg.row);
        break;
      case "reload":
        resync();
        break;
      case "deleted":
        cancelAll();
        onDeleted?.(msg.by);
        break;
    }
  }

  let room = null;
  function joinRoom(name) {
    if (room && room !== name) {
      socket.emit("doc_unsubscribe", "Collection", room);
      socket.emit("doc_close", "Collection", room);
    }
    room = name || null;
    if (room) {
      socket.emit("doc_subscribe", "Collection", room);
      socket.emit("doc_open", "Collection", room);
    }
  }

  function onConnect() {
    connected.value = true;
    if (room) {
      joinRoom(room);
      resync(); // catch up on anything missed while disconnected
    }
  }
  function onDisconnect() {
    connected.value = false;
  }
  function onViewers(msg) {
    if (msg?.doctype === "Collection" && msg.docname === form.name) viewers.value = msg.users || [];
  }
  function onVisible() {
    if (document.visibilityState === "visible") resync();
  }
  function onBeforeUnload(e) {
    if (pendingKeys.size) {
      flush();
      e.preventDefault();
      e.returnValue = "";
    }
  }

  socket.on(SYNC_EVENT_NAME, onSync);
  socket.on("connect", onConnect);
  socket.on("disconnect", onDisconnect);
  socket.on("doc_viewers", onViewers);
  document.addEventListener("visibilitychange", onVisible);
  window.addEventListener("beforeunload", onBeforeUnload);
  watch(() => form.name, joinRoom, { immediate: true });

  onBeforeUnmount(() => {
    flush();
    socket.off(SYNC_EVENT_NAME, onSync);
    socket.off("connect", onConnect);
    socket.off("disconnect", onDisconnect);
    socket.off("doc_viewers", onViewers);
    document.removeEventListener("visibilitychange", onVisible);
    window.removeEventListener("beforeunload", onBeforeUnload);
    joinRoom(null);
  });

  return {
    clientId,
    pendingKeys,
    connected,
    offline,
    viewers,
    merge,
    flush,
    cancelAll,
    touchField,
    touchTally,
    touchRow,
    removeRow,
  };
}
