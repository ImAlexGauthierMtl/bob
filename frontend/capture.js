const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
    console.log("Starting Playwright...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    const screenshotsDir = path.join(__dirname, 'screenshots');
    if (!fs.existsSync(screenshotsDir)) fs.mkdirSync(screenshotsDir);

    const baseUrl = 'http://localhost:4700';

    try {
        console.log("Navigating to Login page...");
        await page.goto(`${baseUrl}/login`);
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

        // Login via UI
        console.log("Typing credentials...");
        await page.fill('input[type="email"]', 'admin@croo.digital');
        await page.press('input[type="email"]', 'Tab');
        await page.fill('input[type="password"]', 'Admin123!');
        await page.press('input[type="password"]', 'Tab');
        await page.click('button[type="submit"]');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);
        console.log("Logged in, current URL:", page.url());

        if (page.url().includes('login')) {
            const errorElement = await page.$('.login-error');
            if (errorElement) {
                const errorText = await errorElement.innerText();
                console.log("Login Error Text:", errorText);
            } else {
                console.log("No .login-error element found on page.");
            }
            await page.screenshot({ path: path.join(screenshotsDir, 'login-error.png'), fullPage: true });
            console.log("Login failed. Check login-error.png");
            return;
        }

        // Ticket 67967: Analytics — Implémenter page BI avec widgets (Dashboard)
        await page.waitForTimeout(2000); // Wait for Plotly to render
        await page.screenshot({ path: path.join(screenshotsDir, '67967.png'), fullPage: true });

        console.log("Navigating to Organizations list...");
        await page.click('a[routerLink="/organizations"]');
        await page.waitForTimeout(2000);
        // Ticket 67966: Organizations - Style filtre All orange/blanc
        await page.screenshot({ path: path.join(screenshotsDir, '67966.png'), fullPage: true });

        console.log("Navigating to Organizations detail...");
        const orgLinks = await page.$$('.org-link');
        if (orgLinks.length > 0) {
            await orgLinks[0].click();
            await page.waitForTimeout(2000);
            // Ticket 67957 & 67960
            await page.screenshot({ path: path.join(screenshotsDir, '67957.png'), fullPage: true });
            await page.screenshot({ path: path.join(screenshotsDir, '67960.png'), fullPage: true });
        } else {
            console.log("No organization found to click");
        }

        console.log("Navigating to Contacts detail...");
        await page.click('a[routerLink="/contacts"]');
        await page.waitForTimeout(2000);
        await page.screenshot({ path: path.join(screenshotsDir, 'contacts_list.png'), fullPage: true });

        const contactLinks = await page.$$('.contact-link');
        if (contactLinks.length > 0) {
            await contactLinks[0].click();
            await page.waitForTimeout(2000);
            // Overview tab (default)
            await page.screenshot({ path: path.join(screenshotsDir, '67958.png'), fullPage: true });

            // Interactions tab
            console.log("Clicking Interactions tab...");
            await page.click('button:has-text("Interactions")');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(screenshotsDir, 'contact_interactions.png'), fullPage: true });

            // Activities tab
            console.log("Clicking Activities tab...");
            await page.click('button:has-text("Activities")');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(screenshotsDir, 'contact_activities.png'), fullPage: true });
            await page.screenshot({ path: path.join(screenshotsDir, '67964.png'), fullPage: true });

            // Notes tab
            console.log("Clicking Notes tab...");
            await page.click('button:has-text("Notes")');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(screenshotsDir, 'contact_notes.png'), fullPage: true });
        } else {
            console.log("No contact found to click");
        }

        console.log("Navigating to Tasks list...");
        await page.click('a[routerLink="/tasks"]');
        await page.waitForTimeout(2000);
        // Ticket 67963 & 67965
        await page.screenshot({ path: path.join(screenshotsDir, '67965.png'), fullPage: true });
        await page.screenshot({ path: path.join(screenshotsDir, '67963.png'), fullPage: true });

        console.log("Navigating to Settings...");
        await page.click('a[routerLink="/settings"]');
        await page.waitForTimeout(1000);
        // Ticket 67961: Settings - Retirer bouton Intégrations
        await page.screenshot({ path: path.join(screenshotsDir, '67961.png'), fullPage: true });

        console.log("Screenshots captured successfully!");
    } catch (error) {
        console.error("Error during capture:", error);
    } finally {
        await browser.close();
    }
})();
