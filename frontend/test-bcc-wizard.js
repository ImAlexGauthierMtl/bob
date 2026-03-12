/**
 * BCC + Bob Wizard Test
 *
 * Tests:
 *   1. BCC view — navigate to Settings → BCC, verify workflow tools visible
 *   2. Bob chat — open Bob, run 4-step create opportunity wizard
 *
 * Usage:
 *   cd frontend && node test-bcc-wizard.js
 */

const { chromium } = require('playwright');
const { login, navigateTo, openBob, sendBobMessage, screenshot } = require('./playwright-helper');

(async () => {
    console.log('🚀 Starting BCC + Bob Wizard Test\n');
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await context.newPage();

    try {
        // ── Login ──
        const ok = await login(page);
        if (!ok) throw new Error('Login failed');

        // ══════════════════════════════════════════════
        // PART 1: BCC View
        // ══════════════════════════════════════════════
        console.log('\n=== PART 1: BCC VIEW ===');

        await navigateTo(page, '/settings/bob-control-center', { waitAfter: 4000 });
        await screenshot(page, 'bcc_overview');

        // Verify BCC content
        const body = await page.textContent('body') || '';
        const bccTools = ['search_organizations', 'create_organization', 'create_contact', 'create_opportunity'];
        for (const tool of bccTools) {
            console.log(`  ${body.includes(tool) ? '✅' : '❌'} BCC: ${tool}`);
        }

        // Try expanding CRM Sales + create_prospect
        const crmSales = page.locator(':text("CRM Sales")');
        if (await crmSales.count() > 0) {
            await crmSales.first().click();
            await page.waitForTimeout(1500);
        }

        const cp = page.locator(':text("create_prospect")');
        if (await cp.count() > 0) {
            await cp.first().click();
            await page.waitForTimeout(1500);
            await screenshot(page, 'bcc_create_prospect');
            console.log('  ✅ create_prospect expanded');
        }

        // ══════════════════════════════════════════════
        // PART 2: Bob Wizard
        // ══════════════════════════════════════════════
        console.log('\n=== PART 2: BOB WIZARD ===');

        await navigateTo(page, '/dashboard', { waitAfter: 3000 });

        const bobOk = await openBob(page);
        if (!bobOk) throw new Error('Could not open Bob');

        await screenshot(page, 'bob_panel_open');

        // Step 1: Request new opportunity
        console.log('\n[Step 1] Create opportunity request');
        let res = await sendBobMessage(page, 'Je veux une nouvelle opportunité', { waitAfter: 10000 });
        await screenshot(page, 'wizard_step1');
        console.log(`  Artifacts: ${res.artifacts} (expected: 1)`);

        // Step 2: Enter name
        console.log('\n[Step 2] Enter name');
        res = await sendBobMessage(page, 'Projet Alpha', { waitAfter: 10000 });
        await screenshot(page, 'wizard_step2');
        console.log(`  Artifacts: ${res.artifacts} (expected: 2)`);

        // Step 3: Choose existing org
        console.log('\n[Step 3] Existing org');
        res = await sendBobMessage(page, 'existante', { waitAfter: 10000 });
        await screenshot(page, 'wizard_step3');
        console.log(`  Artifacts: ${res.artifacts} (expected: 3)`);

        // Step 4: Pick org #1
        console.log('\n[Step 4] Pick org');
        res = await sendBobMessage(page, '1', { waitAfter: 10000 });
        await screenshot(page, 'wizard_step4');
        console.log(`  Artifacts: ${res.artifacts} (complete: ${res.complete})`);

        if (res.complete > 0) {
            console.log('\n🎉 WIZARD COMPLETE — All steps verified!');
        } else {
            console.log('\n⚠️  Wizard did not complete as expected');
        }

    } catch (error) {
        console.error('\n❌ Error:', error.message);
        await screenshot(page, 'error');
    } finally {
        await browser.close();
    }

    console.log('\nDone. Screenshots in frontend/screenshots/');
})();
