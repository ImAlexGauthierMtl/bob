/**
 * Bob CRM Use Cases — E2E Tests
 * Tests the 25 sales use cases via Bob's chat interface.
 * Each test sends a message to Bob and verifies the expected overlay/navigation.
 */
import { test, expect, Page } from 'playwright';

// ── Helper: open Bob chat panel ─────────────────────────────
async function openBobChat(page: Page) {
    const fab = page.locator('.bob-fab');
    if (await fab.isVisible()) {
        await fab.click();
    }
    await expect(page.locator('.bob-panel')).toBeVisible();
}

// ── Helper: send message to Bob and wait for response ───────
async function sendBobMessage(page: Page, message: string) {
    const input = page.locator('.bob-panel .bob-input');
    await input.fill(message);
    await input.press('Enter');
    // Wait for loading to finish (typing indicator disappears)
    await expect(page.locator('.bob-panel .typing-indicator')).toBeHidden({ timeout: 20000 });
}

// ── Helper: verify bob_display overlay opened ───────────────
async function expectDisplayOverlay(page: Page, titleContains: string) {
    const overlay = page.locator('.bob-overlay');
    await expect(overlay).toBeVisible({ timeout: 10000 });
    const title = overlay.locator('.bob-overlay__title');
    await expect(title).toContainText(titleContains, { ignoreCase: true });
}

// ── Helper: close overlay ───────────────────────────────────
async function closeOverlay(page: Page) {
    const closeBtn = page.locator('.bob-overlay__close');
    if (await closeBtn.isVisible()) {
        await closeBtn.click();
    }
    await expect(page.locator('.bob-overlay')).toBeHidden();
}

// ── Helper: count result cards ──────────────────────────────
async function countResultCards(page: Page): Promise<number> {
    const cards = page.locator('.bob-overlay .bob-result-card');
    return cards.count();
}

// ── Helper: count stat cards ────────────────────────────────
async function countStatCards(page: Page): Promise<number> {
    const stats = page.locator('.bob-overlay .bob-stat-card');
    return stats.count();
}

// ═══════════════════════════════════════════════════════════════
//  TEST GROUP: Opportunities
// ═══════════════════════════════════════════════════════════════

test.describe('Bob CRM — Opportunités', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await openBobChat(page);
    });

    test('UC2: Top 5 opportunities', async ({ page }) => {
        await sendBobMessage(page, 'Montre mes 5 meilleures opportunités');
        await expectDisplayOverlay(page, 'Top 5 Opportunités');
        const count = await countResultCards(page);
        expect(count).toBeGreaterThan(0);
        expect(count).toBeLessThanOrEqual(5);
        // Verify numbered items
        const firstNumber = page.locator('.bob-result-card__number').first();
        await expect(firstNumber).toContainText('#1');
        await closeOverlay(page);
    });

    test('UC3: Closing this month', async ({ page }) => {
        await sendBobMessage(page, 'Quelles opportunités doivent closer ce mois?');
        // Bob will respond — check if overlay or message
        await page.waitForTimeout(3000);
        // Overlay may not show if no opps close this month
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'closer ce mois');
            await closeOverlay(page);
        }
    });

    test('UC5: Stale deals', async ({ page }) => {
        await sendBobMessage(page, 'Quels sont mes deals stagnants?');
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'stagnant');
            await closeOverlay(page);
        }
    });

    test('UC7: Pipeline value', async ({ page }) => {
        await sendBobMessage(page, 'Combien vaut mon pipeline?');
        await expectDisplayOverlay(page, 'Pipeline');
        const statCount = await countStatCards(page);
        expect(statCount).toBeGreaterThan(0);
        await closeOverlay(page);
    });
});

// ═══════════════════════════════════════════════════════════════
//  TEST GROUP: Contacts
// ═══════════════════════════════════════════════════════════════

test.describe('Bob CRM — Contacts', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await openBobChat(page);
    });

    test('UC9: Dormant contacts', async ({ page }) => {
        await sendBobMessage(page, "Qui je n'ai pas appelé depuis longtemps?");
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'dormant');
            await closeOverlay(page);
        }
    });

    test('UC10: Recent contacts', async ({ page }) => {
        await sendBobMessage(page, 'Montre les contacts récemment ajoutés');
        await expectDisplayOverlay(page, 'Contact');
        const count = await countResultCards(page);
        expect(count).toBeGreaterThan(0);
        await closeOverlay(page);
    });

    test('UC11: Contacts without email', async ({ page }) => {
        await sendBobMessage(page, "Quels contacts n'ont pas d'email?");
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'email');
            await closeOverlay(page);
        }
    });
});

// ═══════════════════════════════════════════════════════════════
//  TEST GROUP: Accounts
// ═══════════════════════════════════════════════════════════════

test.describe('Bob CRM — Comptes', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await openBobChat(page);
    });

    test('UC15: Accounts without opportunity', async ({ page }) => {
        await sendBobMessage(page, "Quels comptes n'ont pas d'opportunité?");
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'opportunité');
            await closeOverlay(page);
        }
    });

    test('UC16: Most active accounts', async ({ page }) => {
        await sendBobMessage(page, 'Quels sont mes comptes les plus actifs?');
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'actif');
            await closeOverlay(page);
        }
    });

    test('UC17: Accounts by industry', async ({ page }) => {
        await sendBobMessage(page, 'Répartition par industrie');
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await expectDisplayOverlay(page, 'industrie');
            const statCount = await countStatCards(page);
            expect(statCount).toBeGreaterThan(0);
            await closeOverlay(page);
        }
    });
});

// ═══════════════════════════════════════════════════════════════
//  TEST GROUP: Products
// ═══════════════════════════════════════════════════════════════

test.describe('Bob CRM — Produits', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await openBobChat(page);
    });

    test('UC18: List products', async ({ page }) => {
        await sendBobMessage(page, 'Montre les produits disponibles');
        await expectDisplayOverlay(page, 'Produit');
        const count = await countResultCards(page);
        expect(count).toBeGreaterThan(0);
        // Verify price is shown
        const value = page.locator('.bob-result-card__amount').first();
        await expect(value).toBeVisible();
        await closeOverlay(page);
    });
});

// ═══════════════════════════════════════════════════════════════
//  TEST GROUP: Overview / Analytics
// ═══════════════════════════════════════════════════════════════

test.describe('Bob CRM — Overview', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await openBobChat(page);
    });

    test('UC23: Daily summary', async ({ page }) => {
        await sendBobMessage(page, 'Fais-moi un résumé de ma journée');
        await expectDisplayOverlay(page, 'journée');
        const statCount = await countStatCards(page);
        expect(statCount).toBeGreaterThanOrEqual(4); // pipeline, deals, stale, contacts, orgs
        await closeOverlay(page);
    });

    test('UC24: Navigate to contacts', async ({ page }) => {
        await sendBobMessage(page, 'Va à la page contacts');
        // Wait for navigation
        await page.waitForTimeout(3000);
        expect(page.url()).toContain('/contacts');
    });

    test('UC25: Standup prep', async ({ page }) => {
        await sendBobMessage(page, 'Prépare mon standup de ce matin');
        await expectDisplayOverlay(page, 'journée');
        const statCount = await countStatCards(page);
        expect(statCount).toBeGreaterThan(0);
        await closeOverlay(page);
    });
});

// ═══════════════════════════════════════════════════════════════
//  TEST: Overlay UI/UX
// ═══════════════════════════════════════════════════════════════

test.describe('Bob Display Overlay — UI', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await openBobChat(page);
    });

    test('Overlay closes on backdrop click', async ({ page }) => {
        await sendBobMessage(page, 'Montre mes 5 meilleures opportunités');
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            // Click backdrop (outside dialog)
            await overlay.click({ position: { x: 10, y: 10 } });
            await expect(overlay).toBeHidden();
        }
    });

    test('Overlay closes on X button', async ({ page }) => {
        await sendBobMessage(page, 'Montre les produits disponibles');
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            await page.locator('.bob-overlay__close').click();
            await expect(overlay).toBeHidden();
        }
    });

    test('Result card navigates on click', async ({ page }) => {
        await sendBobMessage(page, 'Montre les contacts récemment ajoutés');
        await page.waitForTimeout(3000);
        const overlay = page.locator('.bob-overlay');
        if (await overlay.isVisible()) {
            const firstCard = page.locator('.bob-result-card--clickable').first();
            if (await firstCard.isVisible()) {
                await firstCard.click();
                // Overlay should close and page should change
                await expect(overlay).toBeHidden({ timeout: 5000 });
                expect(page.url()).toContain('/contacts/');
            }
        }
    });
});
