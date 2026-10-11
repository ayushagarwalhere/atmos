import { chromium } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
const downloads=path.resolve('artifacts/browser-downloads');
await fs.mkdir(downloads,{recursive:true});
const browser=await chromium.launch({headless:true,downloadsPath:downloads,executablePath:path.resolve('node_modules/playwright-core/.local-browsers/chromium-1248/chrome-win64/chrome.exe')});
const context=await browser.newContext({acceptDownloads:true});
const page=await context.newPage();
await page.setContent('<button id="export">Export</button>');
await page.evaluate(()=>document.querySelector('button').onclick=()=>{
  const url=URL.createObjectURL(new Blob(['{"status":"ok"}'],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='atmos-download-check.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
const pending=page.waitForEvent('download');
await page.locator('button').click();
const download=await pending;
console.log('Download failure:',await download.failure());
try{console.log('Download path:',await download.path());}catch(error){console.log(error.message)}
await browser.close();
