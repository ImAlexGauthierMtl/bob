"""KB Screenshot Service — Playwright-based CRM screenshot capture.

Uses Playwright to navigate the CRM frontend, execute step-by-step actions,
and capture screenshots for KB article illustrations.
"""

import asyncio
import base64
import os
import structlog
import uuid
from typing import Optional

logger = structlog.get_logger(__name__)

# Directory to store KB screenshots
KB_SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "static", "kb", "screenshots",
)


async def take_step_screenshots(
    steps: list[dict],
    base_url: str = "http://localhost:4700",
    token: str = "",
    viewport_width: int = 1280,
    viewport_height: int = 800,
) -> list[str]:
    """Take screenshots for each step of a KB procedure.

    Each step is a dict with:
        - action: "navigate" | "click" | "fill" | "wait"
        - target: CSS selector or URL path (for navigate)
        - value: optional value for fill actions
        - description: human-readable step description

    Args:
        steps: List of step dictionaries.
        base_url: Frontend base URL.
        token: JWT token for authentication.
        viewport_width: Browser viewport width.
        viewport_height: Browser viewport height.

    Returns:
        List of relative URLs to the saved screenshots.
    """
    from playwright.async_api import async_playwright

    os.makedirs(KB_SCREENSHOTS_DIR, exist_ok=True)
    screenshot_urls = []
    article_id = uuid.uuid4().hex[:8]

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                device_scale_factor=2,  # Retina-quality screenshots
            )

            # Set auth token via localStorage
            page = await context.new_page()
            await page.goto(base_url)

            if token:
                await page.evaluate(
                    f"localStorage.setItem('access_token', '{token}')"
                )
                await page.reload()
                await page.wait_for_load_state("networkidle")

            for i, step in enumerate(steps, 1):
                action = step.get("action", "navigate")
                target = step.get("target", "")
                value = step.get("value", "")

                try:
                    if action == "navigate":
                        url = f"{base_url}{target}" if target.startswith("/") else target
                        await page.goto(url)
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(0.5)  # Let animations settle

                    elif action == "click":
                        await page.click(target, timeout=5000)
                        await asyncio.sleep(0.3)

                    elif action == "fill":
                        await page.fill(target, value, timeout=5000)
                        await asyncio.sleep(0.2)

                    elif action == "wait":
                        wait_ms = int(value) if value else 1000
                        await asyncio.sleep(wait_ms / 1000)

                    # Take screenshot
                    filename = f"{article_id}_step_{i}.png"
                    filepath = os.path.join(KB_SCREENSHOTS_DIR, filename)
                    await page.screenshot(path=filepath, full_page=False)

                    relative_url = f"/static/kb/screenshots/{filename}"
                    screenshot_urls.append(relative_url)

                    logger.info(
                        "kb_screenshot_taken",
                        step=i,
                        action=action,
                        target=target,
                        file=filename,
                    )

                except Exception as e:
                    logger.warning(
                        "kb_screenshot_step_failed",
                        step=i,
                        action=action,
                        target=target,
                        error=str(e),
                    )
                    # Add a placeholder for failed steps
                    screenshot_urls.append("")

            await browser.close()

    except Exception as e:
        logger.error("kb_screenshot_service_error", error=str(e))
        # Return empty URLs for all steps
        return [""] * len(steps)

    return screenshot_urls


def replace_screenshot_placeholders(
    content: str,
    screenshot_urls: list[str],
) -> str:
    """Replace screenshot_placeholder_N markers in markdown with actual URLs.

    Handles both numbered placeholders (screenshot_placeholder_1) and
    the 'screenshot_placeholder_final' marker.
    """
    import re

    # Replace numbered placeholders
    for i, url in enumerate(screenshot_urls, 1):
        placeholder = f"screenshot_placeholder_{i}"
        if url:
            content = content.replace(placeholder, url)
        else:
            # Remove the image line if no screenshot available
            content = re.sub(
                rf"!\[.*?\]\({placeholder}\)\n?",
                "",
                content,
            )

    # Replace 'final' placeholder with last screenshot
    if screenshot_urls and screenshot_urls[-1]:
        content = content.replace(
            "screenshot_placeholder_final",
            screenshot_urls[-1],
        )
    else:
        content = re.sub(
            r"!\[.*?\]\(screenshot_placeholder_final\)\n?",
            "",
            content,
        )

    return content
