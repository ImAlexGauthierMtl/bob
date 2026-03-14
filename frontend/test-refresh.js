const { chromium } = require('playwright');

(async () => {
    console.log('--- Starting Refresh Auth Token Test ---');
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    page.on('console', msg => {
        if (msg.type() === 'error' || msg.type() === 'warning' || msg.text().includes('[AuthService]')) {
            console.log(`[Browser ${msg.type()}] ${msg.text()}`);
        }
    });

    await page.addInitScript(() => {
        const originalRemoveItem = localStorage.removeItem;
        localStorage.removeItem = function (key) {
            console.error(`[LocalStorage Dump] Removing ${key} - Stack: ${new Error().stack}`);
            return originalRemoveItem.call(localStorage, key);
        };
        const originalSetItem = localStorage.setItem;
        localStorage.setItem = function (key, value) {
            console.log(`[LocalStorage Dump] Setting ${key}`);
            return originalSetItem.call(localStorage, key, value);
        };
    });

    try {
        console.log('1. Logging in...');
        await page.goto('http://localhost:4700/login');
        await page.waitForLoadState('networkidle');
        
        await page.fill('#email', 'admin@croo.digital');
        await page.fill('#password', 'Cr00-Adm1n-S3cure!2026');
        
        await Promise.all([
            page.waitForNavigation({ timeout: 10000 }),
            page.click('#login-button')
        ]);

        console.log('2. Checking localStorage after login...');
        let token = await page.evaluate(() => localStorage.getItem('croo_access_token'));
        console.log(`   Token persists: ${!!token}`);

        console.log('3. Refreshing the page...');
        await page.reload({ waitUntil: 'networkidle' });

        console.log('4. Checking localStorage after refresh...');
        token = await page.evaluate(() => localStorage.getItem('croo_access_token'));
        let url = page.url();
        
        console.log(`   Token persists after refresh: ${!!token}`);
        console.log(`   Current URL: ${url}`);
        
        if (!token) {
            console.error('❌ FAILURE: Token was cleared from localStorage upon refresh.');
        } else if (url.includes('/login')) {
            console.error('❌ FAILURE: Redirected to login page despite token existence.');
        } else {
            console.log('✅ SUCCESS: User remained logged in after refresh.');
        }
    } catch (err) {
        console.error('Test execution failed:', err);
    } finally {
        await browser.close();
    }
})();
