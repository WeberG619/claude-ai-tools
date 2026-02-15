// Change category from Writing to Engineering & Architecture
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

  // The modal should still be open from the previous script
  // First check if modal is still open
  const modalCheck = await c.ev(`!!document.querySelector('[role="dialog"]')`);
  if (!modalCheck) {
    console.log('Modal not open, navigating to profile settings...');
    await c.nav('https://www.upwork.com/freelancers/settings/profile');
    await sleep(3000);
    await c.ev(`document.querySelector('button[aria-labelledby="editCategoryLabel"]')?.click()`);
    await sleep(3000);
  }

  // Step 1: Remove "Content Writing" by clicking the Remove button/token
  console.log('=== STEP 1: REMOVING CONTENT WRITING ===');
  const removed = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';

      // Look for the Remove button near "Content Writing" token
      // The modal text showed "Remove" followed by "Content Writing"
      const removeBtn = [...modal.querySelectorAll('button, [role="button"]')].find(el => {
        const text = el.textContent.trim().toLowerCase();
        return text.includes('remove') || el.getAttribute('aria-label')?.toLowerCase().includes('remove');
      });
      if (removeBtn) {
        removeBtn.click();
        return 'Clicked remove: ' + removeBtn.textContent.trim().substring(0, 40);
      }

      // Try clicking the token/chip itself (they sometimes have an X)
      const token = [...modal.querySelectorAll('[class*="token"], [class*="chip"], [class*="tag"]')].find(el =>
        el.textContent.trim().includes('Content Writing')
      );
      if (token) {
        // Look for close/remove button within the token
        const closeBtn = token.querySelector('button, [role="button"], svg, [class*="close"], [class*="remove"]');
        if (closeBtn) {
          closeBtn.click();
          return 'Clicked token close button';
        }
        token.click();
        return 'Clicked token itself';
      }

      return 'No remove button or token found';
    })()
  `);
  console.log(removed);
  await sleep(1500);

  // Check modal state after removing
  console.log('\\n=== MODAL STATE AFTER REMOVE ===');
  const afterRemove = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';
      return modal.innerText.substring(0, 2000);
    })()
  `);
  console.log(afterRemove);

  // Step 2: Click "Engineering & Architecture"
  console.log('\\n=== STEP 2: SELECTING ENGINEERING & ARCHITECTURE ===');
  const selectEng = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';

      // Find the Engineering & Architecture option - look for clickable elements
      const allEls = [...modal.querySelectorAll('*')];
      const engEl = allEls.find(el =>
        el.textContent.trim() === 'Engineering & Architecture' &&
        el.children.length === 0 &&
        el.offsetParent
      );
      if (engEl) {
        // Click the element or its parent (which may be the actual clickable item)
        const clickTarget = engEl.closest('button, a, [role="button"], [role="option"], label, li') || engEl;
        clickTarget.click();
        return 'Clicked Engineering & Architecture: ' + clickTarget.tagName + '.' + clickTarget.className.substring(0, 50);
      }

      // Try broader search
      const engBroad = allEls.find(el =>
        el.textContent.includes('Engineering & Architecture') &&
        (el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'LI' || el.tagName === 'LABEL' || el.getAttribute('role'))
      );
      if (engBroad) {
        engBroad.click();
        return 'Clicked broad match: ' + engBroad.tagName;
      }

      return 'Engineering & Architecture not found';
    })()
  `);
  console.log(selectEng);
  await sleep(2000);

  // Check what subcategories appeared
  console.log('\\n=== SUBCATEGORIES ===');
  const subcats = await c.ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'no modal';

      const checkboxes = [...modal.querySelectorAll('input[type="checkbox"]')]
        .filter(c => c.offsetParent)
        .map(c => ({
          checked: c.checked,
          label: c.closest('label')?.textContent?.trim()?.substring(0, 80)
        }));

      return JSON.stringify({
        modalText: modal.innerText.substring(0, 2000),
        checkboxes
      });
    })()
  `);
  console.log(subcats);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
