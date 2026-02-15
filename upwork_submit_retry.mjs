// Retry submit - check for overlays, loading states, captchas
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Check current state
  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Check if there's a stale error banner - look at the actual DOM state more carefully
  console.log('\n=== CURRENT STATE ===');

  // Check for overlays, modals, loading spinners
  const overlays = await c.ev(`
    (() => {
      const loadings = [...document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="overlay"], [class*="captcha"], [class*="modal"]')]
        .filter(el => el.offsetParent)
        .map(el => el.className.substring(0, 80));
      const iframes = [...document.querySelectorAll('iframe')]
        .filter(f => f.offsetParent)
        .map(f => ({ src: f.src?.substring(0, 80), width: f.offsetWidth, height: f.offsetHeight }));
      return JSON.stringify({ loadings, iframes });
    })()
  `);
  console.log('Overlays/loading:', overlays);

  // Check if the boost connects field has an unexpected value
  const boostField = await c.ev(`
    (() => {
      const input = document.querySelector('input[type="number"]');
      if (input) {
        return JSON.stringify({
          value: input.value,
          placeholder: input.placeholder,
          label: input.closest('label')?.textContent?.trim()?.substring(0, 40),
          parentText: input.parentElement?.innerText?.substring(0, 100)
        });
      }
      return 'no number input';
    })()
  `);
  console.log('Boost field:', boostField);

  // Try clearing the boost connects field (set to 0)
  console.log('\n=== CLEARING BOOST BID ===');
  await c.ev(`
    (() => {
      const input = document.querySelector('input[type="number"]');
      if (input) {
        input.focus();
        input.select();
      }
    })()
  `);
  await sleep(200);

  // Select all and delete
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
  await sleep(100);
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
  await sleep(200);

  // Check the full error banner HTML more carefully
  console.log('\n=== ERROR BANNER DETAIL ===');
  const errorBanner = await c.ev(`
    (() => {
      const alerts = [...document.querySelectorAll('[class*="alert"]')]
        .filter(el => el.offsetParent)
        .map(el => ({
          text: el.textContent.trim().substring(0, 100),
          class: el.className,
          display: getComputedStyle(el).display,
          visibility: getComputedStyle(el).visibility,
          outerHTML: el.outerHTML.substring(0, 200)
        }));
      return JSON.stringify(alerts);
    })()
  `);
  console.log(errorBanner);

  // Scroll to submit button
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for')
      );
      if (btn) btn.scrollIntoView();
    })()
  `);
  await sleep(500);

  // Try submit again
  console.log('\n=== CLICKING SUBMIT ===');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (btn) {
        console.log('Button:', btn.textContent.trim(), 'disabled:', btn.disabled);
        btn.click();
      }
    })()
  `);

  // Wait longer and poll for URL change
  for (let i = 0; i < 10; i++) {
    await sleep(2000);
    const currentUrl = await c.ev('window.location.href');
    if (!currentUrl.includes('apply')) {
      console.log(`Success after ${(i+1)*2}s! URL: ${currentUrl}`);
      const successText = await c.ev('document.body.innerText.substring(0, 800)');
      console.log(successText);
      c.close();
      process.exit(0);
    }
    console.log(`Waiting... ${(i+1)*2}s - still on apply page`);
  }

  // If still here, get current page state
  console.log('\n=== STILL ON APPLY PAGE AFTER 20s ===');
  const finalState = await c.ev(`
    (() => {
      const errors = [...document.querySelectorAll('[class*="error"], [class*="alert-negative"], [class*="form-message-error"]')]
        .filter(el => el.offsetParent)
        .map(el => el.textContent.trim().substring(0, 100));
      const main = document.querySelector('main');
      return JSON.stringify({
        errors,
        pageExcerpt: main?.innerText?.substring(0, 500) || document.body.innerText.substring(0, 500)
      });
    })()
  `);
  console.log(finalState);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
