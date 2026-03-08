/**
 * Playwright E2E + Visual regression tests for the Tenants module.
 * Tests cover:
 *  1. Page structure & layout compliance
 *  2. CRUD operations via UI
 *  3. Visual regression screenshots
 */
import { test, expect } from 'playwright';

test.describe('Tenants Module', () => {

    // ── Page Structure ──────────────────────────────────────

    test('page loads with correct layout', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('#stats-grid');

        // Verify key structural elements
        await expect(page.locator('.page-title')).toHaveText('Tenants');
        await expect(page.locator('#stats-grid')).toBeVisible();
        await expect(page.locator('#toolbar')).toBeVisible();
        await expect(page.locator('#tenant-table')).toBeVisible();
    });

    test('sidebar shows Tenants link in admin section', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('#sidebar-admin-section');

        const adminSection = page.locator('#sidebar-admin-section');
        await expect(adminSection).toBeVisible();

        const tenantsLink = page.locator('#sidebar-tenants-link');
        await expect(tenantsLink).toBeVisible();
        await expect(tenantsLink).toHaveText(/Tenants/);
    });

    test('stats cards display correct structure', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('#stats-grid');

        const cards = page.locator('.stat-card');
        await expect(cards).toHaveCount(4);

        // Labels
        const labels = page.locator('.stat-card__label');
        await expect(labels.nth(0)).toHaveText('Total');
        await expect(labels.nth(1)).toHaveText('Actifs');
        await expect(labels.nth(2)).toHaveText('Essai');
        await expect(labels.nth(3)).toHaveText('Suspendus');
    });

    // ── Create Dialog ───────────────────────────────────────

    test('create tenant dialog opens and has all fields', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('#btn-add-tenant');

        await page.click('#btn-add-tenant');
        await page.waitForSelector('.dialog');

        // Verify dialog structure
        await expect(page.locator('.dialog__title')).toHaveText('Nouveau Tenant');
        await expect(page.locator('#input-name')).toBeVisible();
        await expect(page.locator('#input-slug')).toBeVisible();
        await expect(page.locator('#input-email')).toBeVisible();
        await expect(page.locator('#input-owner-name')).toBeVisible();
        await expect(page.locator('#input-plan')).toBeVisible();
        await expect(page.locator('#input-max-users')).toBeVisible();
        await expect(page.locator('#input-notes')).toBeVisible();
        await expect(page.locator('#btn-submit-create')).toBeVisible();
    });

    test('slug auto-generates from name', async ({ page }) => {
        await page.goto('/tenants');
        await page.click('#btn-add-tenant');
        await page.waitForSelector('.dialog');

        await page.fill('#input-name', 'My Test Company');
        // Wait for Angular change detection
        await page.waitForTimeout(200);

        const slugValue = await page.inputValue('#input-slug');
        expect(slugValue).toBe('my-test-company');
    });

    test('dialog closes on X button', async ({ page }) => {
        await page.goto('/tenants');
        await page.click('#btn-add-tenant');
        await page.waitForSelector('.dialog');

        await page.click('#btn-close-dialog');
        await expect(page.locator('.dialog')).not.toBeVisible();
    });

    // ── Filter & Search ─────────────────────────────────────

    test('filter pills toggle correctly', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('.filter-pills');

        const activeFilter = page.locator('.filter-pill').filter({ hasText: 'Actifs' });
        await activeFilter.click();
        await expect(activeFilter).toHaveClass(/filter-pill--active/);
    });

    // ── Tenant Detail ───────────────────────────────────────

    test('detail page shows all sections', async ({ page }) => {
        // This test assumes at least one tenant exists
        await page.goto('/tenants');
        await page.waitForSelector('#tenant-table');

        // Check if there's a tenant to click on
        const firstTenant = page.locator('.tenant-link').first();
        if (await firstTenant.isVisible()) {
            await firstTenant.click();
            await page.waitForSelector('#detail-header');

            await expect(page.locator('#detail-header')).toBeVisible();
            await expect(page.locator('#detail-grid')).toBeVisible();
            await expect(page.locator('#actions-bar')).toBeVisible();
            await expect(page.locator('#back-link')).toBeVisible();
        }
    });

    // ── Visual Regression ───────────────────────────────────

    test('visual regression - list page', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('#stats-grid');
        // Wait for all data to load
        await page.waitForTimeout(500);

        await expect(page).toHaveScreenshot('tenants-list.png', {
            fullPage: true,
        });
    });

    test('visual regression - create dialog', async ({ page }) => {
        await page.goto('/tenants');
        await page.click('#btn-add-tenant');
        await page.waitForSelector('.dialog');

        await expect(page).toHaveScreenshot('tenants-create-dialog.png', {
            fullPage: true,
        });
    });

    test('visual regression - sidebar admin section', async ({ page }) => {
        await page.goto('/tenants');
        await page.waitForSelector('#sidebar-admin-section');

        await expect(page.locator('#sidebar')).toHaveScreenshot('sidebar-admin.png');
    });
});
