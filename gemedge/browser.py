"""Playwright browser manager for GemEdge."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Tuple
from playwright.async_api import async_playwright, Browser, Page, Route
from gemedge.config import (
    HEADLESS,
    USER_AGENT,
    BLOCKED_RESOURCE_TYPES,
    ROUTE_GLOB
)
from gemedge.logger import logger

@asynccontextmanager
async def get_browser(slow_mo: float = 0.0) -> AsyncIterator[Tuple[Browser, Page]]:
    """Launch Playwright Chromium and return a tuple of browser and page instances, blocking images/fonts."""
    logger.debug("Starting Playwright process...")
    async with async_playwright() as p:
        logger.debug("Launching Chromium browser...")
        browser = await p.chromium.launch(
            headless=HEADLESS,
            slow_mo=slow_mo
        )
        
        context = await browser.new_context(
            user_agent=USER_AGENT
        )
        
        page = await context.new_page()
        
        async def block_resources(route: Route) -> None:
            """Block requests for specified resource types to speed up page loads."""
            resource_type = route.request.resource_type
            if resource_type in BLOCKED_RESOURCE_TYPES:
                logger.debug(f"Blocked resource request for type '{resource_type}': {route.request.url}")
                await route.abort()
            else:
                await route.continue_()
                
        await page.route(ROUTE_GLOB, block_resources)
        
        try:
            yield browser, page
        finally:
            logger.debug("Closing browser context and browser...")
            await context.close()
            await browser.close()
