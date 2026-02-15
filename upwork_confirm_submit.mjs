// Click "Send to Review" in the confirmation modal
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

  // Check if modal is already open
  console.log('=== CHECKING FOR MODAL ===');
  const modalState = await c.ev(`
    (() => {
      var modal = document.querySelector('[role="dialog"]');
      if (modal) {
        var btns = modal.querySelectorAll('button, a');
        var btnTexts = [];
        for (var i = 0; i < btns.length; i++) {
          btnTexts.push({ text: btns[i].textContent.trim(), tag: btns[i].tagName, classes: btns[i].className.substring(0, 60) });
        }
        return JSON.stringify({ open: true, text: modal.innerText.substring(0, 300), buttons: btnTexts });
      }
      return JSON.stringify({ open: false });
    })()
  `);
  console.log(modalState);

  const state = JSON.parse(modalState);

  if (!state.open) {
    // Click Submit for Review first to open the modal
    console.log('\\nModal not open, clicking Submit for Review...');
    await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].offsetParent && btns[i].textContent.trim().includes('Submit for Review')) {
            btns[i].click();
            return 'Clicked';
          }
        }
        return 'Not found';
      })()
    `);
    await sleep(2000);
  }

  // Now click "Send to Review" in the modal
  console.log('\\n=== CLICKING SEND TO REVIEW ===');
  const sendResult = await c.ev(`
    (() => {
      // Look in the modal for "Send to Review" button
      var modal = document.querySelector('[role="dialog"]');
      var scope = modal || document;
      var btns = scope.querySelectorAll('button, a');
      for (var i = 0; i < btns.length; i++) {
        var text = btns[i].textContent.trim();
        if (text === 'Send to Review' || text.includes('Send to Review')) {
          btns[i].click();
          return 'Clicked: ' + text + ' (tag: ' + btns[i].tagName + ', classes: ' + btns[i].className.substring(0, 60) + ')';
        }
      }
      // Also check all buttons on the page
      var allBtns = document.querySelectorAll('button, a');
      var found = [];
      for (var j = 0; j < allBtns.length; j++) {
        var t = allBtns[j].textContent.trim();
        if (t.includes('Send') || t.includes('Review') || t.includes('Confirm') || t.includes('Submit')) {
          found.push(t.substring(0, 40));
        }
      }
      return 'Send to Review button not found. Related buttons: ' + found.join(', ');
    })()
  `);
  console.log(sendResult);

  // Wait for submission
  await sleep(10000);

  // Check result
  const url = await c.ev('window.location.href');
  console.log('\\nURL after submit:', url);

  const result = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log('\\n=== RESULT ===');
  console.log(result);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
