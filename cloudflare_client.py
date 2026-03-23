"""
Cloudflare Browser Rendering API client.

Wraps the /scrape, /json, and /screenshot endpoints with:
- Automatic retry with exponential backoff
- Rate limiting (configurable delay between requests)
- Structured logging
- Timeout handling

Reference: https://developers.cloudflare.com/browser-rendering/rest-api/
"""

import asyncio
import time
import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.settings import settings

logger = logging.getLogger(__name__)


class CloudflareClientError(Exception):
    """Base exception for Cloudflare API errors."""
    pass


class CloudflareRateLimitError(CloudflareClientError):
    """Raised when rate limited by Cloudflare."""
    pass


class CloudflareClient:
    """
    Async client for Cloudflare Browser Rendering REST API.

    Usage:
        async with CloudflareClient() as client:
            data = await client.scrape(url, selectors)
            structured = await client.extract_json(url, schema)
            screenshot = await client.screenshot(url)
    """

    def __init__(self):
        self.base_url = settings.cf_base_url
        self.headers = {
            "Authorization": f"Bearer {settings.cf_api_token}",
            "Content-Type": "application/json",
        }
        self.timeout = settings.request_timeout
        self.delay = settings.scrape_delay_seconds
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _rate_limit(self):
        """Enforce minimum delay between requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.delay:
            wait_time = self.delay - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        self._last_request_time = time.monotonic()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.TimeoutException, CloudflareRateLimitError)
        ),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry {retry_state.attempt_number}/5 — waiting before next attempt... "
            f"({retry_state.outcome.exception().__class__.__name__})"
        ),
    )
    async def _post(self, endpoint: str, payload: dict) -> dict:
        """Make a POST request to the Browser Rendering API with retry logic."""
        await self._rate_limit()

        url = f"{self.base_url}/{endpoint}"
        logger.info(f"POST {endpoint} → {payload.get('url', 'N/A')[:80]}")

        response = await self._client.post(url, json=payload)

        if response.status_code == 429:
            logger.warning("Rate limited (429) — will retry with exponential backoff")
            raise CloudflareRateLimitError("Rate limited by Cloudflare")

        # Log actual status code before raising for better debugging
        if response.status_code >= 400:
            body_preview = response.text[:200] if response.text else "(empty)"
            logger.error(
                f"HTTP {response.status_code} from Cloudflare: {body_preview}"
            )

        response.raise_for_status()
        return response.json()

    # ── /scrape endpoint ──────────────────────────────────────────

    async def scrape(
        self,
        url: str,
        selectors: list[dict[str, str]],
        wait_until: str = "networkidle0",
        user_agent: str | None = None,
    ) -> list[dict]:
        """
        Extract structured data from specific HTML elements using CSS selectors.

        Args:
            url: Target webpage URL
            selectors: List of {"selector": "css_selector"} objects
            wait_until: Page load strategy (networkidle0 for JS-heavy pages)
            user_agent: Optional custom user agent

        Returns:
            List of selector results with text, html, and attributes
        """
        payload = {
            "url": url,
            "elements": selectors,
            "gotoOptions": {"waitUntil": wait_until},
        }
        if user_agent:
            payload["userAgent"] = user_agent

        result = await self._post("scrape", payload)

        if not result.get("success"):
            raise CloudflareClientError(
                f"Scrape failed: {result.get('errors', 'Unknown error')}"
            )

        return result.get("result", [])

    # ── /json endpoint (AI-powered extraction) ────────────────────

    async def extract_json(
        self,
        url: str,
        prompt: str,
        response_format: dict | None = None,
        wait_until: str = "networkidle0",
    ) -> dict:
        """
        Extract structured data from a webpage using AI (Llama 3.3 70B).

        This is the most powerful endpoint — define what you want in natural
        language and/or a JSON schema, and the AI extracts it.

        Args:
            url: Target webpage URL
            prompt: Natural language description of what to extract
            response_format: Optional JSON schema for structured output
            wait_until: Page load strategy

        Returns:
            Extracted data as a dictionary
        """
        payload = {
            "url": url,
            "prompt": prompt,
            "gotoOptions": {"waitUntil": wait_until},
        }
        if response_format:
            payload["response_format"] = response_format

        result = await self._post("json", payload)

        if not result.get("success"):
            raise CloudflareClientError(
                f"JSON extraction failed: {result.get('errors', 'Unknown error')}"
            )

        return result.get("result", {})

    # ── /screenshot endpoint ──────────────────────────────────────

    async def screenshot(
        self,
        url: str,
        full_page: bool = True,
        wait_until: str = "networkidle0",
    ) -> bytes:
        """
        Capture a screenshot of a webpage as evidence.

        Args:
            url: Target webpage URL
            full_page: Whether to capture the full page or just viewport
            wait_until: Page load strategy

        Returns:
            Screenshot as PNG bytes
        """
        payload = {
            "url": url,
            "screenshotOptions": {"fullPage": full_page},
            "gotoOptions": {"waitUntil": wait_until},
        }

        await self._rate_limit()
        response = await self._client.post(
            f"{self.base_url}/screenshot",
            json=payload,
        )
        response.raise_for_status()

        # Screenshot returns binary PNG directly
        return response.content

    # ── /content endpoint (raw HTML) ──────────────────────────────

    async def get_content(
        self,
        url: str,
        wait_until: str = "networkidle0",
    ) -> str:
        """
        Get fully rendered HTML content of a page (after JS execution).
        Useful as fallback when /scrape or /json don't return expected data.

        Returns:
            Rendered HTML as string
        """
        result = await self._post("content", {
            "url": url,
            "gotoOptions": {"waitUntil": wait_until},
        })

        if not result.get("success"):
            raise CloudflareClientError(
                f"Content fetch failed: {result.get('errors', 'Unknown error')}"
            )

        return result.get("result", "")
