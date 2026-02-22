// Save project as draft, then complete description and requirements steps
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
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(8);
      }
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, typeText, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Click "Save & exit" to save as draft
  console.log('=== SAVING AS DRAFT ===');
  const saveExit = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent && btns[i].textContent.trim().includes('Save & exit')) {
          btns[i].click();
          return 'Clicked Save & exit';
        }
      }
      return 'Save & exit not found';
    })()
  `);
  console.log(saveExit);
  await sleep(5000);

  // Check where we ended up
  const url = await c.ev('window.location.href');
  console.log('URL after save:', url);

  const pageText = await c.ev('(document.querySelector("main") || document.body).innerText.substring(0, 2000)');
  console.log(pageText);

  // Look for the draft project and continue editing
  console.log('\n=== FINDING DRAFT PROJECT ===');
  const draftLink = await c.ev(`
    (() => {
      var links = document.querySelectorAll('a');
      for (var i = 0; i < links.length; i++) {
        if (links[i].textContent.trim().includes('custom Revit') || links[i].href.includes('edit')) {
          return { text: links[i].textContent.trim().substring(0, 60), href: links[i].href };
        }
      }
      // Check for edit buttons
      var btns = document.querySelectorAll('button, a');
      var edits = [];
      for (var j = 0; j < btns.length; j++) {
        var t = btns[j].textContent.trim().toLowerCase();
        if (btns[j].offsetParent && (t.includes('edit') || t.includes('continue'))) {
          edits.push({ text: btns[j].textContent.trim(), href: btns[j].href || '' });
        }
      }
      return JSON.stringify(edits);
    })()
  `);
  console.log('Draft:', JSON.stringify(draftLink));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
