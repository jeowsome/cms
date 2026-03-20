/**
 * Composable for making Frappe API calls.
 * Wraps fetch with CSRF token handling and JSON parsing.
 */

function getCsrfToken() {
  // Injected by church_management.html template
  if (window.csrfToken) return window.csrfToken;
  // Fallback: Frappe desk pages
  if (window.frappe?.csrf_token) return window.frappe.csrf_token;
  return "";
}

async function request(url, options = {}) {
  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "X-Frappe-CSRF-Token": getCsrfToken(),
    ...options.headers,
  };

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || error.exc || `HTTP ${res.status}`);
  }

  const data = await res.json();
  return data.message !== undefined ? data.message : data;
}

/**
 * Call a whitelisted Frappe method.
 * @param {string} method - Dotted method path (e.g. "church_management.api.disbursement.get_list")
 * @param {object} params - Method arguments
 */
export function call(method, params = {}) {
  return request("/api/method/" + method, {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/**
 * Get a list of documents.
 */
export function getList(doctype, { fields, filters, orderBy, limit, start } = {}) {
  const params = new URLSearchParams();
  params.set("doctype", doctype);
  if (fields) params.set("fields", JSON.stringify(fields));
  if (filters) params.set("filters", JSON.stringify(filters));
  if (orderBy) params.set("order_by", orderBy);
  if (limit) params.set("limit_page_length", limit);
  if (start) params.set("limit_start", start);

  return request("/api/resource/" + doctype + "?" + params.toString());
}

/**
 * Get a single document.
 */
export function getDoc(doctype, name) {
  return request(`/api/resource/${doctype}/${encodeURIComponent(name)}`);
}

/**
 * Save (create or update) a document.
 */
export function saveDoc(doc) {
  if (doc.name && !doc.__islocal) {
    return request(`/api/resource/${doc.doctype}/${encodeURIComponent(doc.name)}`, {
      method: "PUT",
      body: JSON.stringify(doc),
    });
  }
  return request(`/api/resource/${doc.doctype}`, {
    method: "POST",
    body: JSON.stringify(doc),
  });
}

/**
 * Delete a document.
 */
export function deleteDoc(doctype, name) {
  return request(`/api/resource/${doctype}/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export function useFrappeApi() {
  return { call, getList, getDoc, saveDoc, deleteDoc };
}
