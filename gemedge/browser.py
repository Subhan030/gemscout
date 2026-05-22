"""Reusable Playwright browser context."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Page, Route, async_playwright

from config import HEADLESS

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
BLOCKED_RESOURCE_TYPES = {"image", "font"}


async def _block_heavy_assets(route: Route) -> None:
    """Abort images and fonts to reduce page load cost."""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
        return
    await route.continue_()


@asynccontextmanager
async def browser_context(
    headless: bool = HEADLESS,
    slow_mo: int = 0,
) -> AsyncIterator[tuple[Browser, Page]]:
    """Launch Chromium and yield a reusable browser and page tuple."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = await browser.new_context(user_agent=USER_AGENT)
        await context.route("**/*", _block_heavy_assets)
        page = await context.new_page()
        try:
            yield browser, page
        finally:
            await context.close()
            await browser.close()

