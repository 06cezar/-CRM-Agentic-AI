"""
Orchestrates a single scrape job:
  1. PATCHes core-api to mark job "running"
  2. Runs the scraper, forwarding lead batches to core-api
  3. PATCHes core-api on completion or failure
"""

import logging
from datetime import datetime, timezone

import httpx
from scraper.linkedin import scrape_async, AuthExpiredError

logger = logging.getLogger(__name__)


async def run_job(
    job_id: int,
    user_id: int,
    query: str,
    pages: int,
    cookies_json: str,
    core_api_url: str,
    internal_token: str,
) -> None:
    headers = {"X-Internal-Token": internal_token}

    async def _patch_job(data: dict) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.patch(
                    f"{core_api_url}/scraper/jobs/{job_id}",
                    json=data,
                    headers=headers,
                )
        except httpx.HTTPError as e:
            logger.warning(f"Failed to PATCH job {job_id}: {e}")

    async def on_page_done(leads: list[dict]) -> None:
        payload = {"leads": leads}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{core_api_url}/scraper/jobs/{job_id}/leads",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"Job {job_id}: batch posted — accepted={result.get('accepted')}, skipped={result.get('skipped')}")

                # Update scraped_count
                current_count_resp = await client.get(
                    f"{core_api_url}/scraper/jobs/{job_id}",
                    headers=headers,
                )
                # We just track count via accepted; core-api increments leads_created
        except httpx.HTTPError as e:
            logger.error(f"Job {job_id}: failed to post leads batch: {e}")

    # Mark as running
    await _patch_job({
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    try:
        total = await scrape_async(
            query=query,
            cookies_json_str=cookies_json,
            max_pages=pages,
            on_page_done=on_page_done,
        )
        logger.info(f"Job {job_id} completed: {total} leads scraped")
        await _patch_job({
            "status": "completed",
            "scraped_count": total,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    except AuthExpiredError as e:
        logger.warning(f"Job {job_id} auth expired: {e}")
        await _patch_job({
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        logger.exception(f"Job {job_id} failed unexpectedly: {e}")
        await _patch_job({
            "status": "failed",
            "error_message": f"Unexpected error: {str(e)}",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
