// Service worker: owns auth + all core-api calls. Centralizing fetch here (rather
// than in the content script) keeps the JWT out of the page context and avoids
// page-origin CORS issues.

import { API_BASE, AUTH_COOKIE_NAME } from "./config.js";

async function getAuthToken() {
  // chrome.cookies CAN read httpOnly cookies (page JS cannot).
  const cookie = await chrome.cookies.get({
    url: API_BASE,
    name: AUTH_COOKIE_NAME,
  });
  return cookie ? cookie.value : null;
}

async function apiFetch(path, { method = "GET", body, token } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function sendToTab(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (resp) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(resp);
      }
    });
  });
}

// Guarantees the content script is present in the tab before we message it.
// (Manifest injection only happens on page loads AFTER the extension is
// installed, so an already-open Sales Nav tab would have no receiver.)
async function ensureContentScript(tabId) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    });
  } catch (e) {
    // If it's already injected, a duplicate injection may throw — that's fine.
    console.warn("ensureContentScript:", e.message);
  }
}

// Orchestrates a full scrape and reports progress back to the popup.
async function runScrape({ tabId, query, maxPages }, onProgress) {
  const token = await getAuthToken();
  if (!token) {
    throw new Error("Not logged in. Open the CRM web app and log in first.");
  }

  await ensureContentScript(tabId);

  const job = await apiFetch("/scraper/ext/jobs", {
    method: "POST",
    body: { query },
    token,
  });

  let totalAccepted = 0;
  for (let page = 1; page <= maxPages; page++) {
    const pageResp = await sendToTab(tabId, { type: "SCRAPE_CURRENT_PAGE" });
    const leads = (pageResp && pageResp.leads) || [];

    if (leads.length > 0) {
      const result = await apiFetch(`/scraper/ext/jobs/${job.id}/leads`, {
        method: "POST",
        body: { leads },
        token,
      });
      totalAccepted += result.accepted || 0;
    }

    onProgress({ page, totalAccepted, lastBatch: leads.length });

    if (page < maxPages) {
      const nav = await sendToTab(tabId, { type: "GO_NEXT_PAGE" });
      if (!nav || !nav.hasNext) break;
    }
  }

  await apiFetch(`/scraper/ext/jobs/${job.id}`, {
    method: "PATCH",
    body: { status: "completed" },
    token,
  });

  return { jobId: job.id, totalAccepted };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "START_SCRAPE") {
    (async () => {
      try {
        const result = await runScrape(msg.payload, (progress) => {
          chrome.runtime.sendMessage({ type: "SCRAPE_PROGRESS", progress });
        });
        sendResponse({ ok: true, result });
      } catch (err) {
        sendResponse({ ok: false, error: err.message });
      }
    })();
    return true; // async
  }
});
