import { test, expect } from '@playwright/test';

test('debug login', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
        if (msg.type() === 'error') errors.push(`CONSOLE: ${msg.text()}`);
    });
    page.on('requestfailed', req => {
        errors.push(`NETWORK FAIL: ${req.method()} ${req.url()} - ${req.failure()?.errorText}`);
    });
    page.on('response', resp => {
        if (resp.status() >= 400) {
            errors.push(`HTTP ${resp.status()}: ${resp.request().method()} ${resp.url()}`);
        }
    });

    console.log('Navigating to login...');
    await page.goto('http://localhost:4700/login');

    await page.screenshot({ path: '/tmp/login_form.png' });

    // Fill credentials
    await page.locator('input[type="email"], input[id*="email"], input[name*="email"], input[formControlName="email"]').first().fill('admin@croo.digital');
    await page.locator('input[type="password"], input[formControlName="password"]').first().fill('Admin123!');

    await page.screenshot({ path: '/tmp/login_filled.png' });

    // Click sign in
    await page.locator('button:has-text("Sign In"), button[type="submit"]').first().click();

    // Wait a bit to see what happens
    await page.waitForTimeout(4000);

    const currentUrl = page.url();
    console.log('URL after clicking login:', currentUrl);

    const text = await page.evaluate(() => document.body.innerText);
    console.log('Page text snapshot:', text.substring(0, 300));

    await page.screenshot({ path: '/tmp/login_after.png' });

    console.log('Errors logged:', errors);
});
