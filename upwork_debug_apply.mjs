// Debug: find the actual Apply button on a job page
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

  // Go to a fresh recent job
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=revit+plugin&sort=recency'`);
  await sleep(5000);

  // Click first job
  const firstJob = await c.ev(`
    (() => {
      var links = document.querySelectorAll('a[href*="/jobs/"]');
      for (var i = 0; i < links.length; i++) {
        if (links[i].offsetParent && links[i].textContent.trim().length > 10) {
          var href = links[i].href;
          return href;
        }
      }
      return 'none';
    })()
  `);
  console.log('First job:', firstJob);

  if (firstJob !== 'none') {
    await c.ev(`window.location.href = ${JSON.stringify(firstJob)}`);
    await sleep(5000);
  }

  // Get ALL buttons and links on the page
  console.log('\n=== ALL BUTTONS & LINKS ===');
  const allBtns = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button, a[class*="btn"], a[class*="apply"], [role="button"]');
      var result = [];
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent) {
          var t = btns[i].textContent.trim();
          if (t.length > 0 && t.length < 60) {
            result.push({
              text: t,
              tag: btns[i].tagName,
              href: btns[i].href ? btns[i].href.substring(0, 100) : '',
              classes: (typeof btns[i].className === 'string' ? btns[i].className : '').substring(0, 60),
              dataQa: btns[i].getAttribute('data-qa') || ''
            });
          }
        }
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log(allBtns);

  // Get the full page text to see what the apply section looks like
  console.log('\n=== FULL PAGE TEXT ===');
  const fullText = await c.ev(`(document.querySelector('main') || document.body).innerText`);
  console.log(fullText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
