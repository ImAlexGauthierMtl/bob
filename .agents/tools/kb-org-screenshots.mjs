/**
 * Capture screenshots for "How to Create an Organization" KB article.
 * Uses storageState to preserve auth after login.
 */
import { chromium } from 'playwright';
import fs from 'fs';

const BASE_URL = 'http://localhost:4200';
const OUT = '/home/alexandre/Dev/Croo Digital Experience/croo-digital-experience-v.2.0/frontend/src/assets/kb/screenshots';

fs.mkdirSync(OUT, { recursive: true });

async function main() {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    // 1. Login
    console.log('🔐 Logging in...');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.fill('#email', 'kb@crootest.com');
    await page.fill('#password', 'TestPass123!');
    await page.click('#login-button');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    await page.waitForTimeout(2000);
    console.log(`   ✅ Logged in → ${page.url()}`);

    // Debug: screenshot dashboard
    await page.screenshot({ path: `${OUT}/debug-dashboard.png` });
    console.log('   📷 debug-dashboard.png');

    // 2. Navigate using sidebar link instead of goto (preserves SPA state)
    console.log('\n📷 Navigating to Organizations via sidebar...');
    const orgLink = page.locator('a[href="/organizations"]');
    if (await orgLink.count() > 0) {
        await orgLink.first().click();
    } else {
        // Try direct URL with the stored session
        await page.evaluate(() => {
            window.history.pushState({}, '', '/organizations');
            window.dispatchEvent(new PopStateEvent('popstate'));
        });
    }
    await page.waitForTimeout(3000);
    console.log(`   URL: ${page.url()}`);

    // ═══ STEP 1: Organizations page ═══
    await page.screenshot({ path: `${OUT}/org-step1-page.png` });
    console.log('   ✅ org-step1-page.png');

    // Capture AI insights section
    const aiSection = page.locator('.ai-insights');
    if (await aiSection.count() > 0 && await aiSection.isVisible()) {
        await aiSection.screenshot({ path: `${OUT}/org-ai-insights.png` });
        console.log('   ✅ org-ai-insights.png');
    }

    // ═══ STEP 2: Open dialog ═══
    console.log('\n📷 Opening Add Organization dialog...');
    // Find the button with the + icon in page-header
    const addBtn = page.locator('.btn-accent').filter({ hasText: /Add/ });
    console.log(`   Found ${await addBtn.count()} Add buttons`);
    if (await addBtn.count() > 0) {
        await addBtn.first().click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: `${OUT}/org-step2-dialog.png` });
        console.log('   ✅ org-step2-dialog.png');

        // ═══ STEP 3: Type search ═══
        console.log('\n📷 Typing search query...');
        const searchInput = page.locator('.search-input');
        console.log(`   Found ${await searchInput.count()} search inputs`);
        if (await searchInput.count() > 0) {
            await searchInput.fill('Shopify');
            await page.waitForTimeout(500);
            await page.screenshot({ path: `${OUT}/org-step3-search.png` });
            console.log('   ✅ org-step3-search.png');

            // ═══ STEP 4: Click search → results ═══
            console.log('\n📷 Clicking search...');
            const searchActionBtn = page.locator('.dialog .btn-accent').filter({ hasText: /Search/ });
            console.log(`   Found ${await searchActionBtn.count()} search action buttons`);
            if (await searchActionBtn.count() > 0) {
                await searchActionBtn.click();
                await page.waitForTimeout(8000); // Wait for Google Maps API
                await page.screenshot({ path: `${OUT}/org-step4-results.png` });
                console.log('   ✅ org-step4-results.png');
            }
        }

        // Close
        const closeBtn = page.locator('.dialog__close');
        if (await closeBtn.count() > 0) await closeBtn.click();
    } else {
        console.log('   ⚠️  Add button not found, dumping page content...');
        const html = await page.content();
        console.log(`   Page HTML length: ${html.length}`);
        console.log(`   Has .page-header: ${html.includes('page-header')}`);
        console.log(`   Has btn-accent: ${html.includes('btn-accent')}`);
    }

    await browser.close();

    // Summary
    const files = fs.readdirSync(OUT);
    console.log(`\n🎉 Done! ${files.length} screenshots:`);
    files.forEach(f => {
        const kb = (fs.statSync(`${OUT}/${f}`).size / 1024).toFixed(0);
        console.log(`   ${f} (${kb} KB)`);
    });
}

main().catch(console.error);
