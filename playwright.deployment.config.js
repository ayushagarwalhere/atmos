import { defineConfig } from '@playwright/test';
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';

const browserDir = path.resolve('node_modules/playwright-core/.local-browsers');
const localBrowser = existsSync(browserDir) ? readdirSync(browserDir).find(name => /^chromium-\d+$/.test(name)) : null;
const candidate = localBrowser && path.join(browserDir, localBrowser, 'chrome-win64', 'chrome.exe');
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (candidate && existsSync(candidate) ? candidate : undefined);

export default defineConfig({
  testDir: './tests', testMatch: 'deployment.spec.js', timeout: 60000,
  workers: 1, reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://atmos.test:8000',
    headless: true, reducedMotion: 'reduce',
    launchOptions: {executablePath, args: ['--disable-webgl', '--no-proxy-server', '--host-resolver-rules=MAP atmos.test 127.0.0.1']},
    screenshot: 'only-on-failure',
  },
  projects: [
    {name: 'desktop', use: {viewport: {width: 1280, height: 800}}},
    {name: 'mobile', use: {viewport: {width: 390, height: 844}}},
  ],
});
