import { defineConfig, devices } from 'playwright';

export default defineConfig({
    testDir: './tests',
    timeout: 30000,
    expect: {
        timeout: 5000,
        toHaveScreenshot: {
            maxDiffPixelRatio: 0.05,
        },
    },
    fullyParallel: true,
    forbidOnly: !!process.env['CI'],
    retries: process.env['CI'] ? 2 : 0,
    workers: process.env['CI'] ? 1 : undefined,
    reporter: 'html',
    use: {
        baseURL: 'http://localhost:4200',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
    },
    projects: [
        {
            name: 'setup',
            testMatch: /auth\.setup\.ts/,
        },
        {
            name: 'chromium',
            use: {
                ...devices['Desktop Chrome'],
                viewport: { width: 1440, height: 900 },
                storageState: 'e2e/.auth/user.json',
            },
            dependencies: ['setup'],
        },
    ],
    webServer: [
        {
            command: 'cd ../backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000',
            url: 'http://localhost:8000/health',
            reuseExistingServer: !process.env['CI'],
            timeout: 30000,
        },
        {
            command: 'cd ../frontend && npx ng serve --port 4200',
            url: 'http://localhost:4200',
            reuseExistingServer: !process.env['CI'],
            timeout: 60000,
        },
    ],
});
