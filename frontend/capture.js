/**
 * Screenshot capture for Zoho ticket verification.
 * Refactored to use playwright-helper.js for SPA-safe navigation.
 *
 * Usage:
 *   cd frontend && node capture.js
 */

const { chromium } = require('playwright');
const {
    login,
    navigateTo,
    screenshot,
    SCREENSHOTS_DIR,
} = require('./playwright-helper');

(async () => {
    console.log('Starting Playwright...');
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();

    // API response logging
    page.on('response', async response => {
        if (response.url().includes('/api/v1/')) {
            console.log(`API [${response.request().method()}] ${response.url()} -> ${response.status()}`);
            if (response.url().includes('organizations') && response.request().method() === 'GET' && response.status() === 200) {
                try {
                    const text = await response.text();
                    console.log(`Organizations response body: ${text.substring(0, 300)}...`);
                } catch (e) { }
            }
            if (response.url().includes('/auth/me') && response.request().method() === 'GET' && response.status() === 200) {
                try { const text = await response.text(); console.log(`Auth ME response: ${text}`); } catch (e) { }
            }
        }
    });
    page.on('console', msg => {
        if (msg.type() === 'error' || msg.type() === 'warning') {
            console.log(`Browser ${msg.type()}: ${msg.text()}`);
        }
    });

    try {
        // Login
        const ok = await login(page);
        if (!ok) throw new Error('Login failed');

        // Dashboard / Analytics
        await page.waitForTimeout(2000);
        await screenshot(page, '67967');

        // Organizations list
        console.log('Navigating to Organizations list...');
        await navigateTo(page, '/organizations');
        await screenshot(page, '67966');

        // Organization detail
        console.log('Navigating to Organization detail...');
        const orgLinks = await page.$$('.org-link');
        if (orgLinks.length > 0) {
            await orgLinks[0].click();
            await page.waitForTimeout(2000);
            await screenshot(page, '67957');
            await screenshot(page, '67960');
        } else {
            console.log('No organization found to click');
        }

        // Contacts list
        console.log('Navigating to Contacts...');
        await navigateTo(page, '/contacts');
        await screenshot(page, 'contacts_list');

        // Contact detail
        const contactLinks = await page.$$('.contact-link');
        if (contactLinks.length > 0) {
            await contactLinks[0].click();
            await page.waitForTimeout(2000);
            await screenshot(page, '67958');

            // Tabs
            console.log('Clicking Interactions tab...');
            await page.click('button:has-text("Interactions")');
            await page.waitForTimeout(1000);
            await screenshot(page, 'contact_interactions');

            console.log('Clicking Activities tab...');
            await page.click('button:has-text("Activities")');
            await page.waitForTimeout(1000);
            await screenshot(page, 'contact_activities');
            await screenshot(page, '67964');

            console.log('Clicking Notes tab...');
            await page.click('button:has-text("Notes")');
            await page.waitForTimeout(1000);
            await screenshot(page, 'contact_notes');
        } else {
            console.log('No contact found to click');
        }

        // Tasks list
        console.log('Navigating to Tasks list...');
        await navigateTo(page, '/tasks');
        await screenshot(page, '67965');
        await screenshot(page, '67963');

        // Settings
        console.log('Navigating to Settings...');
        await navigateTo(page, '/settings');
        await screenshot(page, '67961');

        console.log('Screenshots captured successfully!');
    } catch (error) {
        console.error('Error during capture:', error);
    } finally {
        await browser.close();
    }
})();
