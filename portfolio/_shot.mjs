import { chromium } from 'playwright-core';
import { pathToFileURL } from 'url';
import fs from 'fs';
import path from 'path';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DIR = path.dirname(new URL(import.meta.url).pathname.replace(/^\//, ''));
const HTML = path.join(DIR, 'mockup.html');
const OUT = path.join(DIR, 'screens');
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] });
const ctx = await browser.newContext({ viewport: { width: 393, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
await page.goto(pathToFileURL(HTML).href, { waitUntil: 'networkidle' });
await page.waitForTimeout(500);

// full chat (tall)
const cap = page.locator('#cap');
await cap.screenshot({ path: path.join(OUT, 'recepta_chat.png') });
console.log('saved recepta_chat.png');

await browser.close();
console.log('DONE');
