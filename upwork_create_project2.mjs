// Create Project Catalog offering - Custom Revit Plugin Development
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
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(10);
      }
    };
    const pressKey = async (key, code, vk) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key, windowsVirtualKeyCode: vk || 0 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: code || key });
      await sleep(100);
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, selectAll, typeText, pressKey, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Should be on the create page
  let url = await c.ev('window.location.href');
  console.log('URL:', url);

  if (!url.includes('create')) {
    await c.nav('https://www.upwork.com/nx/project-dashboard/create');
    await sleep(3000);
  }

  // ===== STEP 1: OVERVIEW =====
  console.log('========== STEP 1: OVERVIEW ==========');

  // Fill title
  console.log('Setting title...');
  await c.ev(`document.getElementById('project-title-input')?.focus()`);
  await sleep(200);
  // Title: "a custom Revit C# plugin or add-in for your BIM workflow"
  await c.typeText('a custom Revit C# plugin or add-in for your BIM workflow');
  await sleep(500);

  const titleCheck = await c.ev(`document.getElementById('project-title-input')?.value`);
  console.log('Title:', titleCheck);

  // Select category - click "Browse all categories"
  console.log('\nSelecting category...');
  await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button, a')].find(el =>
        el.textContent.trim().toLowerCase().includes('browse all categories') && el.offsetParent
      );
      if (btn) btn.click();
    })()
  `);
  await sleep(2000);

  // Check what appeared
  const catUI = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (modal) return 'MODAL: ' + modal.innerText.substring(0, 2000);
      // Check for expanded category list
      const items = [...document.querySelectorAll('[role="option"], [role="treeitem"], li')]
        .filter(el => el.offsetParent && el.textContent.trim().length < 60)
        .map(el => el.textContent.trim()).slice(0, 20);
      return 'Items: ' + items.join(' | ');
    })()
  `);
  console.log('Category UI:', catUI.substring(0, 1000));

  // Look for Engineering & Architecture or 3D Modeling & CAD
  console.log('\nLooking for Engineering category...');
  const engClicked = await c.ev(`
    (() => {
      // Check in modal or main page
      const container = document.querySelector('[role="dialog"]') || document.body;
      const allEls = [...container.querySelectorAll('*')].filter(el => el.offsetParent);

      // Find "Engineering & Architecture"
      let target = allEls.find(el =>
        el.textContent.trim() === 'Engineering & Architecture' && el.children.length === 0
      );
      if (target) {
        const clickable = target.closest('button, a, [role="button"], [role="option"], [role="treeitem"], li, label') || target;
        clickable.click();
        return 'Clicked Engineering & Architecture: ' + clickable.tagName;
      }

      // Try broader
      target = allEls.find(el =>
        el.textContent.includes('Engineering') && el.textContent.includes('Architecture') &&
        (el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'LI' || el.getAttribute('role'))
      );
      if (target) {
        target.click();
        return 'Clicked broad: ' + target.tagName + ' | ' + target.textContent.trim().substring(0, 40);
      }

      return 'Not found. Available items: ' + allEls
        .filter(el => el.children.length === 0 && el.textContent.trim().length > 3 && el.textContent.trim().length < 50)
        .map(el => el.textContent.trim())
        .slice(0, 30)
        .join(' | ');
    })()
  `);
  console.log(engClicked);
  await sleep(1500);

  // Now look for subcategory - 3D Modeling & CAD
  const subCatClicked = await c.ev(`
    (() => {
      const container = document.querySelector('[role="dialog"]') || document.body;
      const allEls = [...container.querySelectorAll('*')].filter(el => el.offsetParent);

      // Look for 3D Modeling or CAD
      let target = allEls.find(el =>
        (el.textContent.trim() === '3D Modeling & CAD' || el.textContent.trim().includes('3D Modeling')) &&
        el.children.length === 0
      );
      if (target) {
        const clickable = target.closest('button, a, [role="button"], [role="option"], [role="treeitem"], li, label') || target;
        clickable.click();
        return 'Clicked: ' + clickable.textContent.trim().substring(0, 40);
      }

      // List what subcategories are available
      const items = allEls
        .filter(el => el.children.length === 0 && el.textContent.trim().length > 3 && el.textContent.trim().length < 60)
        .map(el => el.textContent.trim())
        .filter((v, i, a) => a.indexOf(v) === i)
        .slice(0, 30);
      return 'Subcategories available: ' + items.join(' | ');
    })()
  `);
  console.log('Subcategory:', subCatClicked);
  await sleep(1500);

  // Check for a deeper subcategory or service type
  const deeperCat = await c.ev(`
    (() => {
      const container = document.querySelector('[role="dialog"]') || document.body;
      const text = container.innerText.substring(0, 2000);
      const items = [...container.querySelectorAll('*')]
        .filter(el => el.offsetParent && el.children.length === 0 && el.textContent.trim().length > 3 && el.textContent.trim().length < 60)
        .map(el => el.textContent.trim())
        .filter((v, i, a) => a.indexOf(v) === i)
        .slice(0, 30);
      return JSON.stringify({ text: text.substring(0, 500), items });
    })()
  `);
  console.log('Deeper:', deeperCat);
  await sleep(1000);

  // Look for a specific service type to select
  const serviceSelect = await c.ev(`
    (() => {
      const container = document.querySelector('[role="dialog"]') || document.body;
      const allEls = [...container.querySelectorAll('*')].filter(el => el.offsetParent);

      // Try clicking any item that mentions "3D" or "CAD" or "BIM" or "Architecture"
      const targets = allEls.filter(el => {
        const t = el.textContent.trim();
        return el.children.length === 0 && t.length > 3 && t.length < 60 &&
          (t.includes('3D') || t.includes('CAD') || t.includes('BIM') || t.includes('Plugin') ||
           t.includes('Modeling') || t.includes('Revit'));
      });

      return targets.map(el => el.textContent.trim()).join(' | ');
    })()
  `);
  console.log('Service options:', serviceSelect);

  // Take a screenshot of current state
  console.log('\n=== CURRENT PAGE STATE ===');
  const pageState = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (modal) return 'MODAL OPEN:\\n' + modal.innerText.substring(0, 1500);
      return 'PAGE:\\n' + (document.querySelector('main') || document.body).innerText.substring(0, 1500);
    })()
  `);
  console.log(pageState);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
