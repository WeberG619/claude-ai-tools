// Preview project and take screenshot
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
import { writeFileSync } from 'fs';

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Open More Project Options and click Preview in one go
  console.log('=== OPENING PREVIEW ===');

  // Click the dropdown trigger
  await c.ev(`
    (() => {
      var triggers = document.querySelectorAll('.action-dropdown, [class*="action-dropdown"]');
      for (var i = 0; i < triggers.length; i++) {
        if (triggers[i].offsetParent) {
          triggers[i].click();
          return 'Clicked trigger';
        }
      }
      // Fallback: click the button
      var btns = document.querySelectorAll('button');
      for (var j = 0; j < btns.length; j++) {
        if (btns[j].offsetParent && btns[j].textContent.trim() === 'More Project Options') {
          btns[j].click();
          return 'Clicked button';
        }
      }
    })()
  `);
  await sleep(500);

  // Now immediately find and click Preview
  const previewResult = await c.ev(`
    (() => {
      // Search all visible text for "Preview"
      var allEls = document.querySelectorAll('a, button, li, span, div');
      for (var i = 0; i < allEls.length; i++) {
        var el = allEls[i];
        var text = el.textContent.trim();
        // Must be exactly "Preview" or a menu item
        if (text === 'Preview' && el.offsetParent) {
          // Check if it's in a dropdown/menu
          var parent = el.closest('.air3-dropdown-menu, [class*="dropdown"], [class*="popper"], [class*="menu"]');
          if (parent) {
            if (el.tagName === 'A' && el.href) {
              return JSON.stringify({ type: 'link', href: el.href });
            }
            el.click();
            return JSON.stringify({ type: 'clicked', tag: el.tagName });
          }
        }
      }

      // Also look for data-qa attributes
      var qaElements = document.querySelectorAll('[data-qa*="preview"]');
      for (var j = 0; j < qaElements.length; j++) {
        if (qaElements[j].offsetParent) {
          qaElements[j].click();
          return JSON.stringify({ type: 'qa-click', qa: qaElements[j].getAttribute('data-qa') });
        }
      }

      return JSON.stringify({ type: 'not-found' });
    })()
  `);
  console.log('Preview:', previewResult);

  const parsed = JSON.parse(previewResult);
  if (parsed.type === 'link') {
    console.log('Navigating to:', parsed.href);
    await c.ev(`window.location.href = ${JSON.stringify(parsed.href)}`);
  }

  await sleep(5000);

  // Check URL
  const url = await c.ev('window.location.href');
  console.log('\nURL:', url);

  // If we're still on dashboard, try navigating to the preview URL directly
  if (url.includes('project-dashboard')) {
    console.log('\nTrying direct preview URL...');
    // The preview URL might follow a pattern
    await c.ev(`window.location.href = 'https://www.upwork.com/services/product/you-will-get-a-custom-revit-c-plugin-or-add-in-for-your-bim-workflow-2021718558562708759'`);
    await sleep(5000);
    const url2 = await c.ev('window.location.href');
    console.log('URL after direct nav:', url2);

    if (url2.includes('project-dashboard') || url2.includes('404')) {
      // Try another URL pattern
      await c.ev(`window.location.href = 'https://www.upwork.com/services/product/development-it-a-custom-revit-c-plugin-or-add-in-for-your-bim-workflow-2021718558562708759'`);
      await sleep(5000);
      const url3 = await c.ev('window.location.href');
      console.log('URL after alt nav:', url3);
    }
  }

  // Get full page text
  const finalUrl = await c.ev('window.location.href');
  console.log('\nFinal URL:', finalUrl);

  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 6000)`);
  console.log('\n=== PAGE CONTENT ===');
  console.log(pageText);

  // Take screenshot and save with Windows path
  const screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  if (screenshot && screenshot.data) {
    const buffer = Buffer.from(screenshot.data, 'base64');
    writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-project-preview.png', buffer);
    console.log('\nScreenshot saved: ' + buffer.length + ' bytes');
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
