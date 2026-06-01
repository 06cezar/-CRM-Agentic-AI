const badge = document.getElementById("pageBadge");
const hint = document.getElementById("hint");
const scrapeBtn = document.getElementById("scrapeBtn");
const pagesInput = document.getElementById("pages");
const statusEl = document.getElementById("status");

const SALES_SEARCH_RE = /^https:\/\/www\.linkedin\.com\/sales\/search\//;

let activeTab = null;

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  activeTab = tab;

  if (tab && SALES_SEARCH_RE.test(tab.url || "")) {
    badge.textContent = "ready";
    badge.className = "badge ok";
    hint.textContent = "You're on a Sales Navigator search. Ready to scrape.";
    scrapeBtn.disabled = false;
  } else {
    badge.textContent = "not on search";
    badge.className = "badge warn";
    hint.textContent =
      "Navigate to a LinkedIn Sales Navigator people-search page, then reopen this.";
    scrapeBtn.disabled = true;
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "SCRAPE_PROGRESS") {
    const { page, totalAccepted, lastBatch } = msg.progress;
    statusEl.innerHTML = `<div>Page ${page}: +${lastBatch} found · <strong>${totalAccepted}</strong> added to CRM</div>`;
  }
});

scrapeBtn.addEventListener("click", () => {
  const maxPages = Math.min(10, Math.max(1, parseInt(pagesInput.value) || 1));
  scrapeBtn.disabled = true;
  statusEl.innerHTML = '<div class="muted">Starting…</div>';

  chrome.runtime.sendMessage(
    {
      type: "START_SCRAPE",
      payload: { tabId: activeTab.id, query: activeTab.url, maxPages },
    },
    (resp) => {
      scrapeBtn.disabled = false;
      if (chrome.runtime.lastError) {
        statusEl.innerHTML = `<div class="err">${chrome.runtime.lastError.message}</div>`;
        return;
      }
      if (resp && resp.ok) {
        statusEl.innerHTML = `<div class="ok" style="color:#16a34a"><strong>Done.</strong> ${resp.result.totalAccepted} leads added to your pipeline. AI research is running on each.</div>`;
      } else {
        statusEl.innerHTML = `<div class="err">${(resp && resp.error) || "Scrape failed"}</div>`;
      }
    }
  );
});

init();
