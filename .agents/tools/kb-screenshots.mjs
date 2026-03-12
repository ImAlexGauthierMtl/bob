#!/usr/bin/env node
/**
 * KB Screenshot Pipeline
 * 
 * Takes automated screenshots of the running application for use in
 * Knowledge Base documentation articles. Logs in, then captures each
 * page/component at 1440×900 viewport.
 *
 * Usage:
 *   node tools/kb-screenshots.mjs                      # All pages
 *   node tools/kb-screenshots.mjs --page=contacts      # Specific page
 *   node tools/kb-screenshots.mjs --page=dashboard --dark  # (future) dark mode
 *
 * Output: frontend/src/assets/kb/screenshots/*.png
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const OUTPUT_DIR = path.join(ROOT, 'frontend', 'src', 'assets', 'kb', 'screenshots');

// ── Config ──────────────────────────────────────────────────

const BASE_URL = process.env.APP_URL || 'http://localhost:4200';
const LOGIN_EMAIL = process.env.APP_EMAIL || 'test@crootest.com';
const LOGIN_PASS = process.env.APP_PASS || 'TestPass123!';
const VIEWPORT = { width: 1440, height: 900 };

// Parse CLI args
const args = process.argv.slice(2);
const pageFilter = args.find(a => a.startsWith('--page='))?.split('=')[1];

// ── Page definitions ────────────────────────────────────────

const PAGES = [
    {
        name: 'dashboard',
        path: '/dashboard',
        wait: 1500,
        captures: [
            { name: 'dashboard-full', type: 'full' },
        ],
    },
    {
        name: 'contacts',
        path: '/contacts',
        wait: 2000,
        captures: [
            { name: 'contacts-list', type: 'full' },
        ],
    },
    {
        name: 'organizations',
        path: '/organizations',
        wait: 2000,
        captures: [
            { name: 'organizations-list', type: 'full' },
        ],
    },
    {
        name: 'opportunities',
        path: '/opportunities',
        wait: 2000,
        captures: [
            { name: 'opportunities-list', type: 'full' },
        ],
    },
    {
        name: 'activities',
        path: '/activities',
        wait: 2000,
        captures: [
            { name: 'activities-overview', type: 'full' },
        ],
    },
    {
        name: 'settings',
        path: '/settings/profile',
        wait: 1500,
        captures: [
            { name: 'settings-profile', type: 'full' },
        ],
    },
    {
        name: 'automation',
        path: '/settings/automation',
        wait: 1500,
        captures: [
            { name: 'settings-automation', type: 'full' },
        ],
    },
    {
        name: 'knowledge-base',
        path: '/knowledge-base',
        wait: 1500,
        captures: [
            { name: 'kb-portal', type: 'full' },
        ],
    },
];

// ── Main ────────────────────────────────────────────────────

async function main() {
    // Ensure output directory
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });

    console.log('🚀 KB Screenshot Pipeline');
    console.log(`   Base URL: ${BASE_URL}`);
    console.log(`   Output:   ${OUTPUT_DIR}`);
    console.log(`   Viewport: ${VIEWPORT.width}×${VIEWPORT.height}`);
    console.log('');

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: VIEWPORT });
    const page = await context.newPage();

    // ── Login ───────────────────────────────
    console.log('🔐 Logging in...');
    try {
        await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });
        await page.fill('#email', LOGIN_EMAIL);
        await page.fill('#password', LOGIN_PASS);
        await page.click('#login-btn');
        await page.waitForURL('**/dashboard', { timeout: 10000 });
        console.log('   ✅ Logged in successfully\n');
    } catch (err) {
        console.log('   ⚠️  Login failed or app not running, continuing with unauthenticated screenshots');
        console.log(`   Error: ${err.message}\n`);
    }

    // ── Capture pages ───────────────────────
    const pagesToCapture = pageFilter
        ? PAGES.filter(p => p.name === pageFilter)
        : PAGES;

    if (pagesToCapture.length === 0) {
        console.log(`❌ No page found for filter: ${pageFilter}`);
        console.log(`   Available: ${PAGES.map(p => p.name).join(', ')}`);
        await browser.close();
        process.exit(1);
    }

    let total = 0;
    for (const pageDef of pagesToCapture) {
        console.log(`📸 ${pageDef.name} → ${pageDef.path}`);
        try {
            await page.goto(`${BASE_URL}${pageDef.path}`, {
                waitUntil: 'networkidle',
                timeout: 15000,
            });
            await page.waitForTimeout(pageDef.wait);

            for (const capture of pageDef.captures) {
                const filename = `${capture.name}.png`;
                const filepath = path.join(OUTPUT_DIR, filename);

                if (capture.type === 'full') {
                    await page.screenshot({ path: filepath, fullPage: true });
                } else if (capture.type === 'element' && capture.selector) {
                    const el = page.locator(capture.selector);
                    if (await el.isVisible()) {
                        await el.screenshot({ path: filepath });
                    } else {
                        console.log(`   ⚠️  Element not found: ${capture.selector}`);
                        continue;
                    }
                }

                const stat = fs.statSync(filepath);
                const sizeKB = (stat.size / 1024).toFixed(0);
                console.log(`   ✅ ${filename} (${sizeKB} KB)`);
                total++;
            }
        } catch (err) {
            console.log(`   ❌ Failed: ${err.message}`);
        }
    }

    await browser.close();

    console.log(`\n🎉 Done! ${total} screenshots captured → ${OUTPUT_DIR}`);
}

main().catch(console.error);
