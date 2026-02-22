// Fix Upwork profile via CDP - navigate to edit pages and fill fields
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
  const c = await connect(tab.webSocketDebuggerUrl);
  console.log('Connected\n');

  // Step 1: Go to profile settings and check current state
  console.log('=== Step 1: Navigate to profile settings ===');
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(2000);

  // Step 2: Try clicking "Edit category" or similar buttons
  console.log('=== Step 2: Find edit buttons ===');
  let editButtons = await c.ev(`
    (() => {
      const buttons = [...document.querySelectorAll('button, a, [role="button"]')];
      return buttons
        .filter(b => {
          const text = (b.textContent || '').toLowerCase();
          const ariaLabel = (b.getAttribute('aria-label') || '').toLowerCase();
          return text.includes('edit') || ariaLabel.includes('edit') ||
                 text.includes('add') || text.includes('change') ||
                 b.querySelector('svg[data-name="edit"], [class*="edit"]');
        })
        .map(b => ({
          tag: b.tagName,
          text: b.textContent.trim().substring(0, 60),
          ariaLabel: b.getAttribute('aria-label') || '',
          href: b.href || '',
          class: b.className.substring(0, 80)
        }))
        .slice(0, 20);
    })()
  `);
  console.log('Edit buttons found:', JSON.stringify(editButtons, null, 2));

  // Step 3: Try the profile overview/edit URL patterns
  console.log('\n=== Step 3: Try profile edit URLs ===');
  const editUrls = [
    'https://www.upwork.com/freelancers/~me/edit',
    'https://www.upwork.com/ab/create-profile/overview',
    'https://www.upwork.com/nx/create-profile/',
    'https://www.upwork.com/ab/profile-setup/overview',
    'https://www.upwork.com/freelancers/settings/profile/overview',
  ];

  for (const url of editUrls) {
    await c.nav(url);
    await sleep(2000);
    const currentUrl = await c.ev('location.href');
    const title = await c.ev('document.title');
    const has404 = await c.ev('document.body.innerText.includes("404") || document.body.innerText.includes("looking for something")');
    console.log(`  ${url}`);
    console.log(`    -> ${currentUrl} | ${title} | 404: ${has404}`);
    if (!has404) {
      const text = await c.ev('document.body.innerText.substring(0, 3000)');
      console.log(`    Content: ${text.substring(0, 500)}`);
    }
  }

  // Step 4: Go back to settings and find all clickable elements
  console.log('\n=== Step 4: Profile settings - all links/buttons ===');
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(2000);

  const allClickable = await c.ev(`
    (() => {
      const items = [...document.querySelectorAll('button, a[href], [role="button"], [data-test]')];
      return items
        .filter(el => {
          const text = (el.textContent || '').trim();
          return text.length > 0 && text.length < 100;
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 80),
          href: el.href || '',
          dataTest: el.getAttribute('data-test') || '',
          ariaLabel: el.getAttribute('aria-label') || ''
        }))
        .slice(0, 40);
    })()
  `);
  console.log(JSON.stringify(allClickable, null, 2));

  // Step 5: Check if we need to click "Edit category"
  console.log('\n=== Step 5: Try clicking Edit category ===');
  const clicked = await c.ev(`
    (() => {
      const el = [...document.querySelectorAll('button, a, [role="button"]')]
        .find(b => b.textContent.trim().toLowerCase().includes('edit category'));
      if (el) { el.click(); return 'clicked: ' + el.textContent.trim(); }
      return 'not found';
    })()
  `);
  console.log('Edit category: ' + clicked);
  await sleep(2000);

  if (clicked.includes('clicked')) {
    const modalText = await c.ev('document.body.innerText.substring(0, 3000)');
    console.log('Modal/page after click:\n' + modalText.substring(0, 1000));
  }

  // Step 6: Try the experience level selector
  console.log('\n=== Step 6: Experience level ===');
  const expClicked = await c.ev(`
    (() => {
      const el = [...document.querySelectorAll('input[type="radio"], label, button')]
        .find(b => (b.textContent || '').includes('Expert'));
      if (el) { el.click(); return 'clicked Expert: ' + el.tagName; }
      return 'not found';
    })()
  `);
  console.log('Experience level: ' + expClicked);
  await sleep(1000);

  // Check what changed
  const afterExp = await c.ev(`
    (() => {
      const radios = [...document.querySelectorAll('input[type="radio"]')];
      return radios.map(r => ({ name: r.name, value: r.value, checked: r.checked, label: r.closest('label')?.textContent?.trim()?.substring(0,40) || '' }));
    })()
  `);
  console.log('Radio states:', JSON.stringify(afterExp, null, 2));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
