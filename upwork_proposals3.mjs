// Navigate to proposals via sidebar link
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

  // Find and click the Proposals link
  console.log('=== FINDING PROPOSALS LINK ===');
  const proposalsLink = await c.ev(`
    (() => {
      var links = document.querySelectorAll('a');
      for (var i = 0; i < links.length; i++) {
        var t = links[i].textContent.trim();
        if (t === 'Proposals' || t === 'Proposals and offers') {
          return links[i].href;
        }
      }
      return 'not found';
    })()
  `);
  console.log('Proposals URL:', proposalsLink);

  if (proposalsLink !== 'not found') {
    await c.ev(`window.location.href = ${JSON.stringify(proposalsLink)}`);
  } else {
    // Try the nav dropdown
    await c.ev(`window.location.href = 'https://www.upwork.com/nx/proposals/'`);
  }
  await sleep(5000);

  let url = await c.ev('window.location.href');
  console.log('URL:', url);

  let text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 6000)`);
  console.log('\n=== PROPOSALS PAGE ===');
  console.log(text);

  // If still not found, try nav menu "Find work > Proposals and offers"
  if (text.includes('404') || text.length < 200) {
    console.log('\nTrying nav dropdown...');
    // Click Find work dropdown
    await c.ev(`
      (() => {
        var btn = document.getElementById('caret-btn-findWorkHome');
        if (btn) { btn.click(); return 'Clicked Find work'; }
        return 'Not found';
      })()
    `);
    await sleep(1000);

    // Find Proposals link in dropdown
    const dropdownLinks = await c.ev(`
      (() => {
        var links = document.querySelectorAll('a');
        var result = [];
        for (var i = 0; i < links.length; i++) {
          var t = links[i].textContent.trim();
          if (t.includes('Proposal') || t.includes('offer')) {
            result.push({ text: t, href: links[i].href });
          }
        }
        return JSON.stringify(result);
      })()
    `);
    console.log('Dropdown links:', dropdownLinks);

    const links = JSON.parse(dropdownLinks);
    if (links.length > 0) {
      await c.ev(`window.location.href = ${JSON.stringify(links[0].href)}`);
      await sleep(5000);
      url = await c.ev('window.location.href');
      console.log('URL:', url);
      text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 6000)`);
      console.log('\n=== PROPOSALS PAGE ===');
      console.log(text);
    }
  }

  // Also check notifications
  console.log('\n=== CHECKING NOTIFICATIONS ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/notifications'`);
  await sleep(5000);

  const notifUrl = await c.ev('window.location.href');
  console.log('URL:', notifUrl);
  const notifText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(notifText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
