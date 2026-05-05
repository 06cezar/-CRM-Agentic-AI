"""
LinkedIn Sales Navigator scraper — service version.
Adapted from demo-scraper/scraper.py for use as a Docker microservice.
"""

import asyncio
import json
import random
import urllib.parse
from typing import Callable, Awaitable

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


class AuthExpiredError(Exception):
    pass


def build_search_url(query: str, page: int = 1) -> str:
    encoded = urllib.parse.quote(query)
    return (
        f"https://www.linkedin.com/sales/search/people"
        f"?query=(keywords:{encoded})"
        f"&page={page}"
    )


def parse_cookie_json(json_str: str) -> list[dict]:
    """Parse LinkedIn cookies from a JSON string (stored in DB)."""
    cookies = json.loads(json_str)
    normalized = []
    for c in cookies:
        normalized.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ".linkedin.com"),
            "path": c.get("path", "/"),
            "expires": c.get("expirationDate") or c.get("expires") or -1,
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
            "sameSite": c.get("sameSite", "None"),
        })
    return normalized


async def extract_leads_from_page(page) -> list[dict]:
    await page.wait_for_load_state("networkidle", timeout=15000)
    await asyncio.sleep(random.uniform(1.5, 2.5))

    leads = await page.evaluate("""
        () => {
            const selectors = [
                '[data-view-name="search-results-lead-result-item"]',
                '.search-results__result-item',
                'li.artdeco-list__item',
            ];
            let cards = [];
            for (const sel of selectors) {
                cards = [...document.querySelectorAll(sel)];
                if (cards.length > 0) break;
            }
            return cards.map(card => {
                const nameEl    = card.querySelector('[data-anonymize="person-name"]') ||
                                  card.querySelector('.result-lockup__name a');
                const titleEl   = card.querySelector('[data-anonymize="title"]') ||
                                  card.querySelector('.result-lockup__highlight-keyword');
                const companyEl = card.querySelector('[data-anonymize="company-name"]') ||
                                  card.querySelector('.result-lockup__position-company a');
                const locEl     = card.querySelector('[data-anonymize="location"]') ||
                                  card.querySelector('.result-lockup__misc-item');
                const linkEl    = card.querySelector('a[href*="/sales/lead/"]') ||
                                  card.querySelector('a[href*="/in/"]');
                return {
                    name:        nameEl    ? nameEl.textContent.trim()    : null,
                    title:       titleEl   ? titleEl.textContent.trim()   : null,
                    company:     companyEl ? companyEl.textContent.trim() : null,
                    location:    locEl     ? locEl.textContent.trim()     : null,
                    profile_url: linkEl    ? linkEl.href                  : null,
                };
            }).filter(l => l.name);
        }
    """)
    return leads


async def has_next_page(page) -> bool:
    selectors = [
        'button[aria-label="Next"]',
        'button.artdeco-pagination__button--next',
        '[data-test-pagination-page-btn="next"]',
    ]
    for sel in selectors:
        btn = page.locator(sel)
        if await btn.count() > 0:
            disabled = await btn.get_attribute("disabled")
            if disabled is None:
                return True
    return False


async def scrape_async(
    query: str,
    cookies_json_str: str,
    max_pages: int,
    on_page_done: Callable[[list[dict]], Awaitable[None]],
) -> int:
    """
    Scrape LinkedIn Sales Navigator and call on_page_done after each page.

    Returns total number of leads scraped.
    Raises AuthExpiredError if LinkedIn redirects to login.
    """
    cookies = parse_cookie_json(cookies_json_str)
    total = 0
    seen: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        await page.goto("https://www.linkedin.com/sales/home", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        if "login" in page.url or "authwall" in page.url:
            await browser.close()
            raise AuthExpiredError("LinkedIn session expired — please re-upload cookies")

        for page_num in range(1, max_pages + 1):
            url = build_search_url(query, page_num)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeout:
                break

            if "login" in page.url or "authwall" in page.url:
                await browser.close()
                raise AuthExpiredError("LinkedIn session expired — please re-upload cookies")

            leads = await extract_leads_from_page(page)
            if not leads:
                break

            # Deduplicate within session
            unique_batch = []
            for lead in leads:
                key = lead.get("profile_url") or lead.get("name")
                if key and key not in seen:
                    seen.add(key)
                    unique_batch.append(lead)

            if unique_batch:
                await on_page_done(unique_batch)
                total += len(unique_batch)

            if page_num < max_pages:
                await asyncio.sleep(random.uniform(2.5, 4.5))

        await browser.close()

    return total
