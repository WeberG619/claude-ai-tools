// View the full project listing with screenshots
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

  // Navigate to project listing
  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  if (!url.includes('/services/product/')) {
    await c.ev(`window.location.href = 'https://www.upwork.com/services/product/you-will-get-a-custom-revit-c-plugin-or-add-in-for-your-bim-workflow-2021718558562708759'`);
    await sleep(8000);
  } else {
    await sleep(3000);
  }

  const finalUrl = await c.ev('window.location.href');
  console.log('Final URL:', finalUrl);

  // Get full page text
  console.log('\n=== FULL PAGE CONTENT ===');
  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText`);
  console.log(pageText);

  // Take screenshot of top
  console.log('\n=== SCREENSHOTS ===');
  await c.ev(`window.scrollTo(0, 0)`);
  await sleep(500);
  let screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-top.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved top screenshot');

  // Scroll down and take more screenshots
  await c.ev(`window.scrollBy(0, 800)`);
  await sleep(500);
  screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-mid1.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved mid1 screenshot');

  await c.ev(`window.scrollBy(0, 800)`);
  await sleep(500);
  screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-mid2.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved mid2 screenshot');

  await c.ev(`window.scrollBy(0, 800)`);
  await sleep(500);
  screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-mid3.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved mid3 screenshot');

  await c.ev(`window.scrollBy(0, 800)`);
  await sleep(500);
  screenshot = await c.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-bottom.png', Buffer.from(screenshot.data, 'base64'));
  console.log('Saved bottom screenshot');

  // Also take a full-page screenshot
  const metrics = await c.send('Page.getLayoutMetrics');
  const fullScreenshot = await c.send('Page.captureScreenshot', {
    format: 'png',
    clip: {
      x: 0,
      y: 0,
      width: metrics.cssContentSize.width,
      height: metrics.cssContentSize.height,
      scale: 1
    },
    captureBeyondViewport: true
  });
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork-listing-full.png', Buffer.from(fullScreenshot.data, 'base64'));
  console.log('Saved full-page screenshot (' + Buffer.from(fullScreenshot.data, 'base64').length + ' bytes)');

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
