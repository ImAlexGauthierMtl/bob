"""Playwright test: BCC view + Bob chat wizard verification.
Strategy: Login via form, then navigate using Angular sidebar links (no full page reloads).
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:4700"
SCREENSHOT_DIR = "/home/alexandre/Dev/Croo Digital Experience/croo-digital-experience-v.2.0/bob-training"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


async def login_and_test(page):
    """Login, then test BCC and Bob without full page reloads."""
    
    # ── LOGIN ──
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)
    
    await page.fill("#email", "admin@croo.digital")
    await page.fill("#password", "Admin123!")
    
    async with page.expect_navigation(timeout=15000):
        await page.click("#login-button")
    
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(3000)
    
    token = await page.evaluate("() => localStorage.getItem('croo_access_token')")
    url = page.url
    print(f"[LOGIN] ✅ Token: {'yes' if token else 'no'} → {url}")
    
    if not token:
        return
    
    # ── Navigate to settings using Angular router ──
    # Instead of full page reload, use router.navigate
    await page.evaluate("() => { const el = document.querySelector('[routerLink*=\"settings\"]') || document.querySelector('a[href*=\"settings\"]'); if (el) el.click(); }")
    await page.wait_for_timeout(2000)
    
    # Or just navigate directly by manipulating the router
    await page.evaluate("""() => {
        // Use Angular router to navigate without full reload
        const ngZone = document.querySelector('app-root');
        if (ngZone) {
            window.history.pushState({}, '', '/settings/bob-control-center');
            window.dispatchEvent(new PopStateEvent('popstate'));
        }
    }""")
    await page.wait_for_timeout(4000)
    
    print(f"[BCC] URL after navigation: {page.url}")
    
    if "bob-control-center" in page.url:
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_bcc_overview.png", full_page=True)
        print("[BCC] ✅ Overview captured")
        
        # Look for BCC content
        body = await page.text_content("body") or ""
        for t in ["CRM Sales", "create_prospect", "search_organizations", "create_opportunity"]:
            print(f"  {'✅' if t in body else '❌'} {t}")
    else:
        print(f"[BCC] ⚠️ URL: {page.url}")
    
    # ── Now test Bob directly on this page ──
    # Go back to dashboard via pushState
    await page.evaluate("""() => {
        window.history.pushState({}, '', '/dashboard');
        window.dispatchEvent(new PopStateEvent('popstate'));
    }""")
    await page.wait_for_timeout(3000)
    
    # ── BOB CHAT TEST ──
    print("\n=== BOB CHAT ===")
    
    fab = page.locator(".bob-fab")
    n = await fab.count()
    print(f"[BOB] FAB count: {n}")
    
    if n == 0:
        # Try waiting more
        await page.wait_for_timeout(3000)
        n = await fab.count()
        print(f"[BOB] FAB count after wait: {n}")
    
    if n == 0:
        # Debug
        all_btns = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map(b => ({
                class: b.className.substring(0, 50),
                text: (b.textContent || '').substring(0, 30)
            }));
        }""")
        print(f"[BOB] All buttons: {all_btns}")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/debug_no_fab.png", full_page=True)
        return
    
    await fab.first.click()
    await page.wait_for_timeout(3000)
    
    inp = page.locator('.bob-panel__field')
    btn = page.locator('.bob-panel__send')
    
    if await inp.count() == 0:
        print("[BOB] ❌ No input found")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/error_no_input.png", full_page=True)
        return
    
    print("[BOB] ✅ Panel open")
    await page.screenshot(path=f"{SCREENSHOT_DIR}/bob_panel_open.png")
    
    async def step(msg, label, fname, wait=10000):
        print(f"\n  [{label}] → '{msg}'")
        await inp.fill(msg)
        await btn.click()
        await page.wait_for_timeout(wait)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/{fname}.png", full_page=True)
        arts = await page.locator(".bob-artifact").count()
        complete = await page.locator(".bob-artifact--complete").count()
        print(f"  [{label}] Artifacts: {arts} (complete: {complete})")
        return arts, complete
    
    # Wizard flow
    await step("Je veux une nouvelle opportunité", "S1", "04_step1")
    await step("Projet Alpha", "S2", "05_step2")
    await step("existante", "S3", "06_step3")
    a, c = await step("1", "S4", "07_step4")
    
    if c > 0:
        print("\n[BOB] ✅ WIZARD COMPLETE!")
    else:
        print("\n[BOB] ⚠️ Wizard may not be complete — check screenshots")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()
        
        try:
            await login_and_test(page)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            await page.screenshot(path=f"{SCREENSHOT_DIR}/error.png", full_page=True)
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
    
    print(f"\nScreenshots → {SCREENSHOT_DIR}/")


asyncio.run(main())
