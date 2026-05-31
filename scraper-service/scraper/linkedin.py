"""
LinkedIn Sales Navigator scraper — service version.
Adapted from demo-scraper/scraper.py for use as a Docker microservice.
"""

import asyncio
import json
import logging
import os
import random
import time
import urllib.parse
from pathlib import Path
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import stealth_async


# Persistent Firefox profile so the browser identity (fingerprint, localStorage,
# rotated tokens) stays stable across runs — LinkedIn revokes sessions presented
# from a never-before-seen fingerprint, so reusing one profile is the core fix.
USER_DATA_DIR = os.getenv("LINKEDIN_PROFILE_DIR", "/data/ff-profile")

# One Firefox process may hold the profile at a time; serialize overlapping jobs.
PROFILE_LOCK = asyncio.Lock()

# Auth cookies that must survive a browser restart. Cookie-Editor often exports
# these as session cookies (no expiry); Firefox won't persist those to disk, so
# we coerce them to a real future expiry — otherwise every run looks "cold".
SESSION_PERSIST = {"li_at", "bscookie", "bcookie", "li_rm", "liap", "JSESSIONID"}


class AuthExpiredError(Exception):
    pass


def build_search_url(query: str, page: int = 1) -> str:
    encoded = urllib.parse.quote(query)
    return (
        f"https://www.linkedin.com/sales/search/people"
        f"?query=(keywords:{encoded})"
        f"&page={page}"
    )


_SAME_SITE_MAP = {
    "strict": "Strict",
    "lax": "Lax",
    "none": "None",
    "no_restriction": "None",
    "unspecified": "Lax",
}

def _normalize_same_site(value: str | None) -> str:
    if not value:
        return "None"
    return _SAME_SITE_MAP.get(value.lower(), "None")


def _normalize_domain(domain: str | None) -> str:
    if not domain:
        return ".linkedin.com"
    # Playwright wants .www.linkedin.com → .linkedin.com for Sales Navigator
    # so that cookies apply to all linkedin.com subdomains including www
    if domain in (".www.linkedin.com", "www.linkedin.com"):
        return ".linkedin.com"
    return domain


def parse_cookie_json(json_str: str) -> list[dict]:
    """Parse LinkedIn cookies from a JSON string (stored in DB)."""
    cookies = json.loads(json_str)
    normalized = []
    for c in cookies:
        name = c.get("name", "")
        exp = c.get("expirationDate") or c.get("expires") or -1
        # Give critical auth cookies a real expiry so Firefox persists them to
        # the profile (session cookies with expires=-1 are dropped on close).
        if exp == -1 and name in SESSION_PERSIST:
            exp = int(time.time()) + 60 * 60 * 24 * 30   # 30 days
        normalized.append({
            "name": name,
            "value": c.get("value", ""),
            "domain": _normalize_domain(c.get("domain")),
            "path": c.get("path", "/"),
            "expires": exp,
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
            "sameSite": _normalize_same_site(c.get("sameSite")),
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


_LOGIN_MARKERS = ("login", "authwall", "checkpoint", "uas/login")


def _is_login_redirect(url: str) -> bool:
    return any(marker in url for marker in _LOGIN_MARKERS)


async def _warmup(page) -> None:
    """
    Build genuine request history like a real session before touching Sales
    Navigator: land on the feed, dwell, scroll and drift the mouse, then enter
    sales/home. Mouse moves use steps= so they emit real intermediate events
    instead of teleporting.
    """
    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeout:
        pass
    await asyncio.sleep(random.uniform(2.5, 4.5))

    for _ in range(random.randint(3, 6)):
        await page.mouse.move(
            random.randint(100, 1300),
            random.randint(100, 800),
            steps=random.randint(5, 15),
        )
        await page.mouse.wheel(0, random.randint(300, 900))
        await asyncio.sleep(random.uniform(0.8, 2.0))

    await page.goto("https://www.linkedin.com/sales/home", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(random.uniform(3.0, 5.0))
    await page.mouse.move(random.randint(200, 800), random.randint(200, 600), steps=10)
    await asyncio.sleep(random.uniform(1.0, 2.0))


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

    profile_path = Path(USER_DATA_DIR)
    profile_path.mkdir(parents=True, exist_ok=True)
    # Cold = first ever run for this profile (Firefox hasn't written prefs yet).
    is_cold = not any(profile_path.iterdir())

    # Only one Firefox process may own a persistent profile at a time.
    async with PROFILE_LOCK:
        async with async_playwright() as pw:
            context = await pw.firefox.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=False,   # real headful Firefox under Xvfb — more authentic
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) "
                    "Gecko/20100101 Firefox/125.0"
                ),
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Linux x86_64' });
            """)

            # Seed cookies ONCE on a cold profile. On a warm profile, reuse the
            # persisted session — re-injecting stale exported cookies would clobber
            # tokens LinkedIn rotated and look like a replay attack.
            if is_cold:
                await context.add_cookies(cookies)
                logger.info("Cold profile: seeded cookies from DB.")
            else:
                existing = {c["name"] for c in await context.cookies("https://www.linkedin.com")}
                if "li_at" not in existing:
                    logger.warning("Warm profile missing li_at; re-seeding li_at only.")
                    await context.add_cookies([c for c in cookies if c["name"] == "li_at"])
                else:
                    logger.info("Warm profile: reusing persisted session, no cookie injection.")

            # Verify critical cookies are present
            stored = await context.cookies("https://www.linkedin.com")
            stored_names = {c["name"] for c in stored}
            logger.info(f"Cookies in context: {sorted(stored_names)}")
            for critical in ("li_at", "JSESSIONID", "bscookie"):
                logger.info(f"  {critical}: {'PRESENT' if critical in stored_names else 'MISSING'}")

            page = context.pages[0] if context.pages else await context.new_page()
            await stealth_async(page)

            await _warmup(page)

            final_url = page.url
            logger.info(f"After warm-up landed on: {final_url}")
            if _is_login_redirect(final_url):
                await context.close()
                raise AuthExpiredError(
                    f"Redirected to {final_url} — session not accepted. "
                    "If the real browser also logged out, the token family was revoked server-side."
                )

            for page_num in range(1, max_pages + 1):
                url = build_search_url(query, page_num)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except PlaywrightTimeout:
                    break

                if _is_login_redirect(page.url):
                    await context.close()
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

            await context.close()

    return total
