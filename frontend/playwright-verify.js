/**
 * Playwright Quick Verify — Auto-check pages after frontend changes.
 *
 * Usage:
 *   node playwright-verify.js                        # Verify all main pages
 *   node playwright-verify.js /dashboard /contacts   # Verify specific pages
 *
 * Exit codes:
 *   0 = all pages OK
 *   1 = at least one page failed (redirect to /login, crash, etc.)
 */

const { chromium } = require('playwright');
const { login, navigateTo, screenshot, ROUTE_MAP } = require('./playwright-helper');

const ALL_MAIN_PAGES = [
    '/dashboard',
    '/organizations',
    '/contacts',
    '/opportunities',
    '/tasks',
    '/analytics',
    '/settings',
    '/settings/bob-control-center',
];

(async () => {
    // Parse args: pages to verify
    const args = process.argv.slice(2);
    const pages = args.length > 0 ? args : ALL_MAIN_PAGES;

    // Validate routes
    for (const p of pages) {
        if (!ROUTE_MAP[p]) {
            console.error(`❌ Unknown route: ${p}`);
            console.error(`   Available: ${Object.keys(ROUTE_MAP).join(', ')}`);
            process.exit(1);
        }
    }

    console.log(`🔍 Playwright Verify — ${pages.length} page(s)\n`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();

    let failures = 0;

    try {
        const ok = await login(page);
        if (!ok) {
            console.error('❌ Login failed');
            process.exit(1);
        }

        for (const route of pages) {
            const navOk = await navigateTo(page, route, { waitAfter: 3000 });
            const url = page.url();
            const onLogin = url.includes('/login');
            const name = route.replace(/\//g, '_').substring(1) || 'root';

            if (!navOk || onLogin) {
                console.log(`  ❌ ${route} → FAILED (url=${url})`);
                await screenshot(page, `verify_FAIL_${name}`);
                failures++;
            } else {
                console.log(`  ✅ ${route} → OK`);
                await screenshot(page, `verify_${name}`);
            }
        }

    } catch (error) {
        console.error(`\n❌ Crash: ${error.message}`);
        await screenshot(page, 'verify_CRASH');
        failures++;
    } finally {
        await browser.close();
    }

    console.log(`\n${'═'.repeat(40)}`);
    if (failures === 0) {
        console.log(`✅ PASS — ${pages.length}/${pages.length} pages OK`);
        process.exit(0);
    } else {
        console.log(`❌ FAIL — ${failures}/${pages.length} page(s) failed`);
        process.exit(1);
    }
})();
