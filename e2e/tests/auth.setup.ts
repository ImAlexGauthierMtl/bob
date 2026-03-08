/**
 * Playwright auth setup — creates a logged-in super_admin session.
 * Saves storage state to e2e/.auth/user.json for reuse.
 */
import { test as setup, expect } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const authFile = path.join(__dirname, '..', '.auth', 'user.json');

setup('authenticate as super_admin', async ({ request }) => {
    // Ensure .auth directory exists
    const authDir = path.dirname(authFile);
    if (!fs.existsSync(authDir)) {
        fs.mkdirSync(authDir, { recursive: true });
    }

    // Login via API
    const response = await request.post('http://localhost:8000/api/v1/auth/login', {
        data: {
            email: 'admin@croo.digital',
            password: process.env['ADMIN_PASSWORD'] || 'admin123',
        },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();

    // Save auth state with token in localStorage format
    const storageState = {
        cookies: [],
        origins: [
            {
                origin: 'http://localhost:4200',
                localStorage: [
                    { name: 'access_token', value: body.access_token },
                    { name: 'user_id', value: body.user_id || '' },
                ],
            },
        ],
    };

    fs.writeFileSync(authFile, JSON.stringify(storageState, null, 2));
});
