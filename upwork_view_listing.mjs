// View updated project listing with screenshots
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

  // Navigate to the listing
  await c.ev(`window.location.href = 'https://www.upwork.com/services/product/you-will-get-a-custom-revit-c-plugin-or-add-in-for-your-bim-workflow-2021718558562708759'`);
  await sleep(6000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Scroll to top and take screenshots
  await c.ev(`window.scrollTo(0, 0)`);
  await sleep(500);

  let screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-v2-top.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved top');

  await c.ev(`window.scrollBy(0, 800)`);
  await sleep(500);
  screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-v2-mid.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved mid');

  await c.ev(`window.scrollBy(0, 800)`);
  await sleep(500);
  screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-v2-bottom.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved bottom');

  // Get the pricing table text specifically
  const pricingText = await c.ev(`
    (() => {
      var main = document.querySelector('main') || document.body;
      var text = main.innerText;
      var start = text.indexOf("What's included");
      var end = text.indexOf('Frequently asked');
      if (start >= 0 && end > start) return text.substring(start, end);
      return text.substring(0, 4000);
    })()
  `);
  console.log('\\n=== PRICING TABLE ===');
  console.log(pricingText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
