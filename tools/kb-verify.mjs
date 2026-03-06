import { chromium } from 'playwright';
import fs from 'fs';

const BASE_URL = 'http://localhost:4200';
const OUT = '/tmp/kb-verify';
fs.mkdirSync(OUT, { recursive: true });

async function main() {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    // Login
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.fill('#email', 'kb@crootest.com');
    await page.fill('#password', 'TestPass123!');
    await page.click('#login-button');
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    await page.waitForTimeout(2000);
    console.log(`✅ Logged in → ${page.url()}`);

    // Navigate to KB using the footer link (SPA navigation)
    console.log('\n📷 KB Portal via footer link...');
    const kbLink = page.locator('a[routerLink="/knowledge-base"], a[href="/knowledge-base"]');
    const linkCount = await kbLink.count();
    console.log(`   Found ${linkCount} KB links`);

    if (linkCount > 0) {
        await kbLink.first().click();
        await page.waitForTimeout(3000);
    } else {
        // Fallback: use Angular router directly
        console.log('   Using Angular router.navigate...');
        await page.evaluate(() => {
            const router = window.ng?.getComponent(document.querySelector('app-root'))?.router;
            if (router) router.navigate(['/knowledge-base']);
        });
        await page.waitForTimeout(3000);
    }
    console.log(`   URL: ${page.url()}`);
    await page.screenshot({ path: `${OUT}/kb-portal.png`, fullPage: true });
    console.log('   ✅ kb-portal.png');

    // Navigate to the article
    console.log('\n📷 KB Article...');
    const articleLink = page.locator('a[href*="how-to-create"]');
    const articleCount = await articleLink.count();
    console.log(`   Found ${articleCount} article links`);

    if (articleCount > 0) {
        await articleLink.first().click();
        await page.waitForTimeout(3000);
    } else {
        // Direct URL navigation - try clicking on the article title if present
        console.log('   Trying direct URL...');
        await page.evaluate(() => {
            window.location.hash = '';
            const a = document.createElement('a');
            a.href = '/knowledge-base/how-to-create-an-organization';
            a.click();
        });
        await page.waitForTimeout(3000);
    }
    console.log(`   URL: ${page.url()}`);
    await page.screenshot({ path: `${OUT}/kb-article.png`, fullPage: true });
    console.log('   ✅ kb-article.png');

    await browser.close();
    console.log('\n🎉 Done!');
}

main().catch(console.error);
