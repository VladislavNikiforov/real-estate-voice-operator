/**
 * Gmail sender via existing Chrome remote debugging session (default 9222).
 *
 * Usage:
 *   node send-gmail.js --to "a@b.com" --subject "Hello" --body "Text" [--file "C:\\path\\doc.pdf"] [--port 9333]
 *
 * Defaults:
 *   --port 9222
 *
 * Behavior:
 *   - Connects to Chrome via http://127.0.0.1:<port>
 *   - Navigates to https://mail.google.com/
 *   - Clicks Compose
 *   - Fills To / Subject / Body
 *   - Optionally attaches file if provided AND port is default 9222
 *     (per your rule: skip attaching if --port is used)
 *   - Clicks Send and waits for "Message sent" toast
 */

const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const key = a.slice(2);
    const val = argv[i + 1];
    if (val && !val.startsWith('--')) {
      out[key] = val;
      i++;
    } else {
      out[key] = true;
    }
  }
  return out;
}

async function getWsEndpoint(port) {
  const debugUrl = `http://127.0.0.1:${port}`;
  const res = await fetch(`${debugUrl}/json/version`);
  if (!res.ok) throw new Error(`Could not reach Chrome at ${debugUrl}. Start Chrome with --remote-debugging-port=${port}`);
  const data = await res.json();
  if (!data.webSocketDebuggerUrl) throw new Error('webSocketDebuggerUrl missing from /json/version');
  return data.webSocketDebuggerUrl;
}

async function clickByText(page, text) {
  const lower = text.toLowerCase();
  await page.waitForFunction((t) => {
    const els = Array.from(document.querySelectorAll('div[role="button"],button'));
    return els.some(e => (e.textContent || '').trim().toLowerCase() === t);
  }, { timeout: 60000 }, lower);

  await page.evaluate((t) => {
    const els = Array.from(document.querySelectorAll('div[role="button"],button'));
    const el = els.find(e => (e.textContent || '').trim().toLowerCase() === t);
    el?.click();
  }, lower);
}

async function main() {
  const args = parseArgs(process.argv);
  const to = args.to;
  const subject = args.subject || '';
  const body = args.body || '';
  const filePath = args.file || '';
  const port = args.port ? Number(args.port) : 9222;

  if (!to) throw new Error('Missing required --to "email@domain.com"');
  if (Number.isNaN(port) || port <= 0) throw new Error('Invalid --port');

  const usingCustomPort = !!args.port && port !== 9222;
  const shouldAttach = !!filePath && !usingCustomPort; // your rule

  if (shouldAttach) {
    if (!fs.existsSync(filePath)) throw new Error(`Attachment not found: ${filePath}`);
    const stat = fs.statSync(filePath);
    if (!stat.isFile()) throw new Error(`Attachment is not a file: ${filePath}`);
  }

  const ws = await getWsEndpoint(port);
  const browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: null });

  const pages = await browser.pages();
  const page = pages.length ? pages[0] : await browser.newPage();

  await page.bringToFront();
  await page.goto('https://mail.google.com/', { waitUntil: 'domcontentloaded' });

  if (!page.url().includes('mail.google.com')) {
    throw new Error(`Not on Gmail (are you logged in?). Current URL: ${page.url()}`);
  }

  await clickByText(page, 'Compose');

  await page.waitForFunction(() => {
    return !!document.querySelector('textarea[name="to"], input[aria-label="To recipients"], textarea[aria-label="To recipients"]');
  }, { timeout: 60000 });

  await page.evaluate(() => {
    const el = document.querySelector('textarea[name="to"], input[aria-label="To recipients"], textarea[aria-label="To recipients"]');
    if (!el) throw new Error('To field not found');
    el.focus();
    if ('value' in el) el.value = '';
  });
  await page.keyboard.type(to, { delay: 20 });
  await page.keyboard.press('Enter');

  await page.waitForSelector('input[name="subjectbox"]', { timeout: 60000 });
  await page.click('input[name="subjectbox"]', { clickCount: 3 });
  if (subject) await page.keyboard.type(subject, { delay: 5 });

  await page.waitForSelector('div[aria-label="Message Body"]', { timeout: 60000 });
  await page.click('div[aria-label="Message Body"]');
  if (body) await page.keyboard.type(body, { delay: 3 });

  if (shouldAttach) {
    const selector = 'input[type="file"][name="Filedata"], input[type="file"]';

    const existing = await page.$(selector);
    if (!existing) {
      await page.waitForFunction(() => {
        const els = Array.from(document.querySelectorAll('div[role="button"],button'));
        return els.some(e => {
          const tt = (e.getAttribute('data-tooltip') || '').toLowerCase();
          const al = (e.getAttribute('aria-label') || '').toLowerCase();
          return tt.includes('attach files') || al.includes('attach files');
        });
      }, { timeout: 60000 });

      await page.evaluate(() => {
        const els = Array.from(document.querySelectorAll('div[role="button"],button'));
        const btn = els.find(e => ((e.getAttribute('data-tooltip') || '').toLowerCase().includes('attach files')))
          || els.find(e => ((e.getAttribute('aria-label') || '').toLowerCase().includes('attach files')));
        btn?.click();
      });
    }

    const input = await page.waitForSelector(selector, { timeout: 60000 });
    await input.uploadFile(filePath);

    const base = path.basename(filePath);
    await page.waitForFunction((name) => {
      return document.body && document.body.innerText && document.body.innerText.includes(name);
    }, { timeout: 60000 }, base);

    console.log(`Attached: ${filePath}`);
  } else if (filePath && usingCustomPort) {
    console.log('Note: --port was provided; per configuration, skipping attachment.');
  }

  await page.waitForFunction(() => {
    const btns = Array.from(document.querySelectorAll('div[role="button"],button'));
    return btns.some(b => (b.getAttribute('data-tooltip') || '').toLowerCase().startsWith('send') || (b.textContent || '').trim().toLowerCase() === 'send');
  }, { timeout: 60000 });

  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('div[role="button"],button'));
    const send = btns.find(b => (b.getAttribute('data-tooltip') || '').toLowerCase().startsWith('send'))
      || btns.find(b => (b.textContent || '').trim().toLowerCase() === 'send');
    send?.click();
  });

  await page.waitForFunction(() => {
    const el = document.querySelector('span.bAq');
    return !!el && (el.textContent || '').toLowerCase().includes('message sent');
  }, { timeout: 30000 });

  console.log('SUCCESS: Email sent.');
  await browser.disconnect();
}

main().catch((e) => {
  console.error('FAILED:', e && e.message ? e.message : e);
  process.exitCode = 1;
});
