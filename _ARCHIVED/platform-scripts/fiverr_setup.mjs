// Navigate to Fiverr and check if we can set up a gig
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
      if (msg.method === 'Page.javascriptDialogOpening') {
        const mid = id++;
        ws.send(JSON.stringify({ id: mid, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      }
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
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();

  // Check for existing Fiverr tab
  let tab = pages.find(p => p.url.includes('fiverr.com'));

  if (!tab) {
    // Open Fiverr in a new tab by navigating the Upwork tab (or use current tab)
    tab = pages.find(p => p.url.includes('upwork.com'));
    if (!tab) tab = pages[0];
  }

  if (!tab) { console.log('No browser tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Navigate to Fiverr
  console.log('Navigating to Fiverr...');
  try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
  await c.ev(`window.location.href = 'https://www.fiverr.com'`);
  await sleep(5000);

  // Check if we're logged in
  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  const pageText = await c.ev(`document.body.innerText.substring(0, 2000)`);
  console.log('\n=== PAGE STATE ===');
  console.log(pageText.substring(0, 1000));

  // Check for login state
  const isLoggedIn = await c.ev(`
    (() => {
      var body = document.body.innerText;
      // If we see "Join" or "Sign In" prominently, we're not logged in
      if (body.includes('Become a Seller') || body.includes('seller dashboard')) return 'logged_in_seller';
      if (body.includes('Start Selling')) return 'logged_in_not_seller';
      var navBtns = document.querySelectorAll('a, button');
      for (var i = 0; i < navBtns.length; i++) {
        var t = navBtns[i].textContent.trim();
        if (t === 'Sign In' || t === 'Join') return 'not_logged_in';
        if (t === 'Switch to Selling' || t === 'Selling') return 'logged_in';
      }
      return 'unknown';
    })()
  `);
  console.log('Login state:', isLoggedIn);

  // Try to navigate to seller dashboard / create gig
  if (isLoggedIn.includes('logged_in')) {
    console.log('\nNavigating to seller dashboard...');
    await c.ev(`window.location.href = 'https://www.fiverr.com/seller_dashboard'`);
    await sleep(5000);

    const dashUrl = await c.ev('window.location.href');
    console.log('Dashboard URL:', dashUrl);

    const dashText = await c.ev(`document.body.innerText.substring(0, 2000)`);
    console.log('Dashboard:', dashText.substring(0, 800));

    // Try to navigate to create gig
    console.log('\nNavigating to create gig...');
    await c.ev(`window.location.href = 'https://www.fiverr.com/manage_gigs/new'`);
    await sleep(5000);

    const gigUrl = await c.ev('window.location.href');
    console.log('Gig URL:', gigUrl);

    const gigText = await c.ev(`document.body.innerText.substring(0, 2000)`);
    console.log('Gig page:', gigText.substring(0, 1000));
  } else {
    console.log('Not logged into Fiverr. Would need to create/log into account first.');
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
