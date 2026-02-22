// Fix Upwork category from Writing to Engineering & Architecture
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

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
    const nav = async (url) => { await send('Page.navigate', { url }); await sleep(5000); };
    const click = async (x, y) => {
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
      await sleep(300);
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(20);
      }
    };
    const pressKey = async (key, code, vk) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key, windowsVirtualKeyCode: vk || 0 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: code || key });
      await sleep(50);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, click, selectAll, typeText, pressKey, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Navigate to profile settings where category is configured
  console.log('=== CHECKING PROFILE SETTINGS ===');
  await c.nav('https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca');
  await sleep(3000);

  // Look for category-related elements or "Profile settings" link
  const categoryInfo = await c.ev(`
    (() => {
      // Check for category text anywhere on page
      const allText = document.body.innerText;
      const writingIdx = allText.indexOf('Writing');
      const categoryIdx = allText.indexOf('ategory');
      const specialtyIdx = allText.indexOf('pecialt');

      // Look for edit buttons related to category
      const editBtns = [...document.querySelectorAll('button[aria-label]')]
        .filter(b => b.offsetParent)
        .map(b => b.getAttribute('aria-label'));

      // Look for "Profile settings" link
      const settingsLink = [...document.querySelectorAll('a')]
        .filter(a => a.textContent.includes('Profile settings') || a.href?.includes('settings'))
        .map(a => ({ text: a.textContent.trim(), href: a.href }));

      return JSON.stringify({
        editButtons: editBtns,
        settingsLinks: settingsLink,
        hasWritingText: writingIdx > -1 ? allText.substring(Math.max(0, writingIdx - 30), writingIdx + 50) : 'not found',
        hasCategoryText: categoryIdx > -1 ? allText.substring(Math.max(0, categoryIdx - 30), categoryIdx + 50) : 'not found'
      });
    })()
  `);
  console.log('Category info:', categoryInfo);

  // Try the profile settings page
  console.log('\\n=== NAVIGATING TO PROFILE SETTINGS ===');
  await c.nav('https://www.upwork.com/nx/settings/contact-info');
  await sleep(3000);

  const settingsText = await c.ev('document.body.innerText.substring(0, 3000)');
  console.log('Settings page:', settingsText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
