import { defineConfig } from '@playwright/test';
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
const browserDir=path.resolve('node_modules/playwright-core/.local-browsers');
const localBrowser=existsSync(browserDir)?readdirSync(browserDir).find(name=>/^chromium-\d+$/.test(name)):null;
const localExecutable=localBrowser?path.join(browserDir,localBrowser,'chrome-win64','chrome.exe'):undefined;
export default defineConfig({
 testDir:'./tests',testMatch:'**/*.spec.js',timeout:90000,workers:1,reporter:'list',
 projects:[{name:'interactions',grepInvert:/capture desktop/,use:{launchOptions:{downloadsPath:path.resolve('artifacts/browser-downloads'),executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (localExecutable&&existsSync(localExecutable)?localExecutable:undefined),args:['--disable-webgl']}}},{name:'webgl-render',grep:/capture desktop/}],
 use:{baseURL:process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5173',headless:true,reducedMotion:'reduce',
 launchOptions:{downloadsPath:path.resolve('artifacts/browser-downloads'),executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (localExecutable&&existsSync(localExecutable)?localExecutable:undefined),args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}}
});
