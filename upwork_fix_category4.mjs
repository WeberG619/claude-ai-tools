// Fix Upwork category - find and click the correct Edit category element
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
        await sleep(20);
      }
    };
    const pressKey = async (key, code, vk) => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: code || key, windowsVirtualKeyCode: vk || 0 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: code || key });
      await sleep(50);
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

  // Make sure we're on the profile settings page
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(3000);

  // Get the HTML around "Edit category"
  console.log('=== EDIT CATEGORY HTML ===');
  const html = await c.ev(`
    (() => {
      // Find all elements containing "Edit category"
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode: (node) => node.textContent.includes('Edit category') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT
      });
      const results = [];
      while (walker.nextNode()) {
        const textNode = walker.currentNode;
        const parent = textNode.parentElement;
        results.push({
          parentTag: parent.tagName,
          parentClass: parent.className,
          parentId: parent.id,
          grandParentTag: parent.parentElement?.tagName,
          grandParentClass: parent.parentElement?.className,
          outerHTML: parent.outerHTML.substring(0, 300),
          isVisible: parent.offsetParent !== null,
          rect: parent.getBoundingClientRect()
        });
      }
      // Also check for any button/a containing "Edit" near "category" section
      const allClickable = [...document.querySelectorAll('a, button, [role="button"]')]
        .filter(el => {
          const text = el.textContent.trim().toLowerCase();
          return (text.includes('edit') && text.includes('categor')) || el.getAttribute('aria-label')?.toLowerCase().includes('categor');
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          href: el.href || '',
          ariaLabel: el.getAttribute('aria-label'),
          class: el.className,
          outerHTML: el.outerHTML.substring(0, 300),
          rect: el.getBoundingClientRect()
        }));
      return JSON.stringify({ textMatches: results, clickable: allClickable });
    })()
  `);
  console.log(html);

  // Also look at the category section HTML specifically
  console.log('\\n=== CATEGORY SECTION HTML ===');
  const sectionHTML = await c.ev(`
    (() => {
      // Find the Writing/Content Writing text and get surrounding section
      const allEls = [...document.querySelectorAll('*')];
      const writingEl = allEls.find(el => el.textContent.trim() === 'Writing' && el.children.length === 0 && el.offsetParent);
      if (writingEl) {
        // Go up several levels to find the section
        let section = writingEl;
        for (let i = 0; i < 6; i++) {
          if (section.parentElement) section = section.parentElement;
        }
        return section.outerHTML.substring(0, 2000);
      }
      return 'Writing element not found';
    })()
  `);
  console.log(sectionHTML);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
