/**
 * Quick Playwright verification — Bob "Ajouter un compte" flow.
 * Opens Bob, clicks the quick action, captures screenshots.
 */

const { chromium } = require('playwright');
const { login, navigateTo, openBob, sendBobMessage, screenshot } = require('./playwright-helper');
const path = require('path');

const OUT_DIR = path.join(__dirname, 'screenshots', 'bob-verify');

(async () => {
    console.log('🔍 Verifying Bob "Ajouter un compte" flow...\n');
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();

    try {
        const ok = await login(page);
        if (!ok) throw new Error('Login failed');

        // Navigate to organizations page first
        await navigateTo(page, '/organizations');

        // Open Bob
        const bobOk = await openBob(page);
        if (!bobOk) throw new Error('Bob panel did not open');

        // Screenshot 1: Bob panel open with quick actions
        await screenshot(page, 'bob_panel_open', { dir: OUT_DIR });

        // Click "Ajouter un compte" quick action
        const quickBtn = page.locator('.bob-quick:has-text("Ajouter un compte")');
        if (await quickBtn.count() > 0) {
            await quickBtn.click();
            console.log('[verify] Clicked "Ajouter un compte" quick action');
            await page.waitForTimeout(10000); // Wait for Bob response
            await screenshot(page, 'bob_add_account_response', { dir: OUT_DIR });
        } else {
            console.log('[verify] ⚠️ "Ajouter un compte" quick action not found');
            // Try sending the message manually
            await sendBobMessage(page, 'Ajouter un compte', { waitAfter: 10000 });
            await screenshot(page, 'bob_add_account_response', { dir: OUT_DIR });
        }

        // Check for artifacts and links
        const artifacts = await page.locator('.bob-artifact').count();
        const links = await page.locator('.bob-artifact__link').count();
        const enrichmentArtifact = await page.locator('.bob-artifact--enrichment').count();

        console.log(`\n📊 Results:`);
        console.log(`   Artifacts: ${artifacts}`);
        console.log(`   Links: ${links}`);
        console.log(`   Enrichment artifacts: ${enrichmentArtifact}`);

        console.log('\n✅ Verification complete');
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        await screenshot(page, 'bob_verify_error', { dir: OUT_DIR });
    } finally {
        await browser.close();
    }
})();
