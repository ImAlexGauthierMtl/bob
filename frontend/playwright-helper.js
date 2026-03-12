/**
 * Playwright Helper — SPA-safe navigation for Croo Digital Experience
 *
 * IMPORTANT: Never use page.goto() after login. Angular SPA re-bootstraps on
 * full reload and the auth guard may clear the JWT before localStorage is read.
 * Always navigate via routerLink clicks to stay within Angular's router.
 *
 * Usage:
 *   const { login, navigateTo, openBob, sendBobMessage, screenshot } = require('./playwright-helper');
 */

const path = require('path');
const fs = require('fs');

// ─── Config ───────────────────────────────────────────────────────────

const BASE_URL = process.env.CROO_URL || 'http://localhost:4700';
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

// ─── Route Map ────────────────────────────────────────────────────────
// Each route maps to { selector, parent? }
// If parent is defined, we navigate there first (2-hop SPA navigation).

const ROUTE_MAP = {
    '/dashboard': { selector: 'a[routerLink="/dashboard"]' },
    '/organizations': { selector: 'a[routerLink="/organizations"]' },
    '/contacts': { selector: 'a[routerLink="/contacts"]' },
    '/opportunities': { selector: 'a[routerLink="/opportunities"]' },
    '/tasks': { selector: 'a[routerLink="/tasks"]' },
    '/analytics': { selector: 'a[routerLink="/analytics"]' },
    '/team': { selector: 'a[routerLink="/team"]' },
    '/settings': { selector: 'a[routerLink="/settings"]' },
    '/settings/bob-control-center': { selector: 'a[routerLink="bob-control-center"]', parent: '/settings' },
    '/template': { selector: 'a[routerLink="/template"]' },
    '/knowledge-base': { selector: 'a[routerLink="/knowledge-base"]' },
    '/tenants': { selector: 'a[routerLink="/tenants"]' },
    '/usage-logs': { selector: 'a[routerLink="/usage-logs"]' },
    '/bob-assistant': { selector: 'a[routerLink="/bob-assistant"]' },
};

// ─── Helpers ──────────────────────────────────────────────────────────

/**
 * Login via the Angular login form.
 * After success, the page lands on /dashboard (or /select-organization).
 * @param {import('playwright').Page} page
 * @param {object} opts
 * @param {string} opts.email
 * @param {string} opts.password
 * @returns {Promise<boolean>} true if login succeeded
 */
async function login(page, opts = {}) {
    const email = opts.email || 'admin@croo.digital';
    const password = opts.password || 'Admin123!';

    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    await page.fill('#email', email);
    await page.fill('#password', password);

    // Click and wait for Angular navigation
    await Promise.all([
        page.waitForNavigation({ timeout: 15000 }).catch(() => { }),
        page.click('#login-button'),
    ]);

    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const token = await page.evaluate(() => localStorage.getItem('croo_access_token'));
    const url = page.url();

    if (token && !url.includes('/login')) {
        console.log(`[playwright-helper] ✅ Logged in → ${url}`);
        return true;
    }

    console.log(`[playwright-helper] ❌ Login failed (url=${url}, token=${!!token})`);
    return false;
}

/**
 * Navigate to a route using Angular routerLink clicks (SPA-safe).
 * Never causes a full page reload.
 * @param {import('playwright').Page} page
 * @param {string} route — e.g. '/settings/bob-control-center'
 * @param {object} opts
 * @param {number} opts.waitAfter — ms to wait after navigation (default 2000)
 * @returns {Promise<boolean>} true if navigation succeeded
 */
async function navigateTo(page, route, opts = {}) {
    const waitAfter = opts.waitAfter || 2000;
    const entry = ROUTE_MAP[route];

    if (!entry) {
        console.log(`[playwright-helper] ⚠️ Unknown route: ${route}`);
        console.log(`[playwright-helper]   Known routes: ${Object.keys(ROUTE_MAP).join(', ')}`);
        return false;
    }

    // If route has a parent, navigate there first
    if (entry.parent) {
        const parentOk = await navigateTo(page, entry.parent, { waitAfter: 1500 });
        if (!parentOk) return false;
    }

    const link = page.locator(entry.selector).first();
    const count = await link.count();

    if (count === 0) {
        console.log(`[playwright-helper] ❌ Link not found: ${entry.selector}`);
        return false;
    }

    await link.click();
    await page.waitForTimeout(waitAfter);

    console.log(`[playwright-helper] → ${route} (url=${page.url()})`);
    return true;
}

/**
 * Open the Bob chat panel by clicking the FAB.
 * @param {import('playwright').Page} page
 * @returns {Promise<boolean>} true if panel opened
 */
async function openBob(page) {
    const fab = page.locator('.bob-fab');
    if (await fab.count() === 0) {
        console.log('[playwright-helper] ❌ Bob FAB not found');
        return false;
    }

    await fab.click();
    await page.waitForTimeout(2000);

    const panel = page.locator('.bob-panel');
    if (await panel.count() === 0) {
        console.log('[playwright-helper] ❌ Bob panel did not open');
        return false;
    }

    console.log('[playwright-helper] ✅ Bob panel opened');
    return true;
}

/**
 * Close the Bob chat panel.
 * @param {import('playwright').Page} page
 */
async function closeBob(page) {
    const fab = page.locator('.bob-fab--open');
    if (await fab.count() > 0) {
        await fab.click();
        await page.waitForTimeout(500);
    }
}

/**
 * Send a message to Bob and wait for the response.
 * Bob panel must already be open.
 * @param {import('playwright').Page} page
 * @param {string} message — message to send
 * @param {object} opts
 * @param {number} opts.waitAfter — ms to wait for response (default 8000)
 * @returns {Promise<{artifacts: number, complete: number}>}
 */
async function sendBobMessage(page, message, opts = {}) {
    const waitAfter = opts.waitAfter || 8000;

    const input = page.locator('.bob-panel__field');
    const sendBtn = page.locator('.bob-panel__send');

    if (await input.count() === 0) {
        console.log('[playwright-helper] ❌ Bob input not found (is panel open?)');
        return { artifacts: 0, complete: 0 };
    }

    await input.fill(message);
    await sendBtn.click();
    await page.waitForTimeout(waitAfter);

    const artifacts = await page.locator('.bob-artifact').count();
    const complete = await page.locator('.bob-artifact--complete').count();

    console.log(`[playwright-helper] Bob ← "${message}" → artifacts=${artifacts} (complete=${complete})`);
    return { artifacts, complete };
}

/**
 * Take a screenshot saved to the screenshots directory.
 * @param {import('playwright').Page} page
 * @param {string} name — filename without extension
 * @param {object} opts
 * @param {boolean} opts.fullPage — default true
 * @param {string} opts.dir — override screenshot directory
 * @returns {Promise<string>} absolute path to the screenshot
 */
async function screenshot(page, name, opts = {}) {
    const dir = opts.dir || SCREENSHOTS_DIR;
    const fullPage = opts.fullPage !== undefined ? opts.fullPage : true;

    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    const filePath = path.join(dir, `${name}.png`);
    await page.screenshot({ path: filePath, fullPage });
    console.log(`[playwright-helper] 📸 ${name}.png`);
    return filePath;
}

/**
 * Get the text content of Bob's messages area.
 * @param {import('playwright').Page} page
 * @returns {Promise<string>}
 */
async function getBobMessages(page) {
    const area = page.locator('.bob-panel__messages');
    if (await area.count() === 0) return '';
    return (await area.textContent()) || '';
}

// ─── Exports ──────────────────────────────────────────────────────────

module.exports = {
    BASE_URL,
    SCREENSHOTS_DIR,
    ROUTE_MAP,
    login,
    navigateTo,
    openBob,
    closeBob,
    sendBobMessage,
    screenshot,
    getBobMessages,
};
