// Navigate to project gallery and upload PDF
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

  // Check current URL
  const url = await c.ev('window.location.href');
  console.log('Current URL:', url);

  // Check current page - look for edit options
  console.log('\n=== CHECKING PAGE STATE ===');
  const pageInfo = await c.ev(`
    (() => {
      var text = (document.querySelector('main') || document.body).innerText.substring(0, 2000);
      // Look for edit/manage buttons or links
      var links = document.querySelectorAll('a, button');
      var editLinks = [];
      for (var i = 0; i < links.length; i++) {
        var t = links[i].textContent.trim();
        if (t.includes('Edit') || t.includes('More') || t.includes('Gallery') || t.includes('Manage') || t.includes('Project Options')) {
          editLinks.push({ text: t.substring(0, 50), tag: links[i].tagName, href: links[i].href ? links[i].href.substring(0, 100) : '' });
        }
      }
      return JSON.stringify({ excerpt: text.substring(0, 500), editLinks });
    })()
  `);
  console.log(pageInfo);

  // Try navigating directly to the gallery step
  console.log('\n=== NAVIGATING TO GALLERY ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/project-dashboard/2021718558562708759?step=Gallery'`);
  await sleep(5000);

  const newUrl = await c.ev('window.location.href');
  console.log('New URL:', newUrl);

  const galleryText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 2000)`);
  console.log('\n=== GALLERY PAGE ===');
  console.log(galleryText);

  // Check for PDF file input
  const pdfInput = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="file"]');
      var result = [];
      for (var i = 0; i < inputs.length; i++) {
        result.push({
          accept: inputs[i].accept || '',
          visible: !!inputs[i].offsetParent,
          id: inputs[i].id || '',
          classes: inputs[i].className.substring(0, 60),
          parentText: inputs[i].parentElement ? inputs[i].parentElement.textContent.trim().substring(0, 60) : ''
        });
      }
      return JSON.stringify(result, null, 2);
    })()
  `);
  console.log('\n=== FILE INPUTS ===');
  console.log(pdfInput);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
