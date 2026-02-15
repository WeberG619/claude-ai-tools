// Close the overlay modal and submit
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Check the modal content
  console.log('=== MODAL CONTENT ===');
  const modalContent = await c.ev(`
    (() => {
      const modal = document.querySelector('.air3-modal, [class*="fullscreen"]');
      if (modal) {
        const text = modal.innerText;
        const buttons = [...modal.querySelectorAll('button, a')]
          .filter(b => b.offsetParent)
          .map(b => ({
            text: b.textContent.trim().substring(0, 40),
            class: b.className.substring(0, 60),
            tag: b.tagName
          }));
        return JSON.stringify({ text: text.substring(0, 1000), buttons });
      }
      return 'no modal';
    })()
  `);
  console.log(modalContent);

  // Try closing the modal - click close button or dismiss
  console.log('\n=== CLOSING MODAL ===');
  const closed = await c.ev(`
    (() => {
      // Try close button
      const closeBtn = document.querySelector('.air3-modal-close, [class*="modal-close"]');
      if (closeBtn) { closeBtn.click(); return 'Clicked close button'; }

      // Try clicking any button that says "close", "dismiss", "ok", "continue", "I understand"
      const modal = document.querySelector('.air3-modal, [class*="fullscreen"]');
      if (modal) {
        const btns = [...modal.querySelectorAll('button')].filter(b => b.offsetParent);
        for (const btn of btns) {
          const text = btn.textContent.trim().toLowerCase();
          if (text.includes('close') || text.includes('dismiss') || text.includes('ok') ||
              text.includes('continue') || text.includes('understand') || text.includes('got it') ||
              text.includes('agree') || text.includes('accept')) {
            btn.click();
            return 'Clicked: ' + btn.textContent.trim();
          }
        }
        // If no obvious button, click the first button in the footer
        const footer = modal.querySelector('.air3-modal-footer');
        if (footer) {
          const footerBtns = [...footer.querySelectorAll('button')].filter(b => b.offsetParent);
          if (footerBtns.length > 0) {
            footerBtns[footerBtns.length - 1].click();
            return 'Clicked last footer button: ' + footerBtns[footerBtns.length - 1].textContent.trim();
          }
        }
      }

      // Try clicking overlay
      const overlay = document.querySelector('.overlay');
      if (overlay) { overlay.click(); return 'Clicked overlay'; }

      return 'Nothing to close';
    })()
  `);
  console.log(closed);
  await sleep(2000);

  // Check if modal is gone
  const modalGone = await c.ev(`
    (() => {
      const modal = document.querySelector('.air3-modal');
      const overlay = document.querySelector('.overlay');
      return JSON.stringify({
        modalVisible: modal ? getComputedStyle(modal).display !== 'none' : false,
        overlayVisible: overlay ? getComputedStyle(overlay).display !== 'none' : false
      });
    })()
  `);
  console.log('Modal state:', modalGone);

  // Try submit
  console.log('\n=== SUBMITTING ===');
  const submitResult = await c.ev(`
    (() => {
      const btn = [...document.querySelectorAll('button')].find(b =>
        b.textContent.trim().toLowerCase().includes('send for') && b.offsetParent
      );
      if (btn && !btn.disabled) {
        btn.click();
        return 'Clicked: ' + btn.textContent.trim();
      }
      return btn ? 'Button disabled' : 'Not found';
    })()
  `);
  console.log(submitResult);

  // Wait and check
  for (let i = 0; i < 8; i++) {
    await sleep(2000);
    const currentUrl = await c.ev('window.location.href');
    if (!currentUrl.includes('apply')) {
      console.log(`\nSUCCESS after ${(i+1)*2}s! URL: ${currentUrl}`);
      const text = await c.ev('document.body.innerText.substring(0, 500)');
      console.log(text);
      c.close();
      process.exit(0);
    }

    // Check for new modal
    const newModal = await c.ev(`
      (() => {
        const modal = document.querySelector('.air3-modal');
        if (modal && getComputedStyle(modal).display !== 'none') {
          return 'MODAL: ' + modal.innerText.substring(0, 300);
        }
        return null;
      })()
    `);
    if (newModal) console.log(`${(i+1)*2}s: ` + newModal);
    else console.log(`Waiting... ${(i+1)*2}s`);
  }

  // Final state
  const finalText = await c.ev('document.body.innerText.substring(0, 1000)');
  console.log('\nFinal state:', finalText.substring(0, 500));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
