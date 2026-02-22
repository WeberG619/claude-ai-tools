// Try to log into Gumroad via Google OAuth (leveraging existing Chrome Google session)
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
  let tab = pages.find(p => p.url.includes('gumroad'));
  if (!tab) tab = pages[0];
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  // Navigate to Gumroad login if not already there
  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  if (!url.includes('gumroad.com/login')) {
    try { await c.ev(`window.onbeforeunload = null`); } catch(e) {}
    await c.ev(`window.location.href = 'https://gumroad.com/login'`);
    await sleep(3000);
  }

  // Click Google login button
  console.log('Clicking Google login...');
  const googleClick = await c.ev(`
    (() => {
      var links = document.querySelectorAll('a, button');
      for (var i = 0; i < links.length; i++) {
        var t = links[i].textContent.trim().toLowerCase();
        if (t === 'google' || t.includes('continue with google') || t.includes('sign in with google')) {
          links[i].click();
          return 'Clicked: ' + links[i].textContent.trim() + ' href=' + (links[i].href || 'none');
        }
      }
      return 'not found';
    })()
  `);
  console.log(googleClick);
  await sleep(8000);

  // Check if we're now on Google OAuth page or back on Gumroad
  const allPages = await getPages();
  console.log('\n=== ALL TABS ===');
  for (const p of allPages) {
    console.log(' -', p.url.substring(0, 100));
  }

  // Find the Gumroad or Google tab
  const gumTab = allPages.find(p => p.url.includes('gumroad.com') && !p.url.includes('login'));
  const googleTab = allPages.find(p => p.url.includes('accounts.google.com'));

  if (gumTab) {
    console.log('\nGumroad dashboard found!');
    const c2 = await connect(gumTab.webSocketDebuggerUrl);
    const dashText = await c2.ev(`document.body.innerText.substring(0, 1000)`);
    console.log('Dashboard:', dashText.substring(0, 500));
    c2.close();
  } else if (googleTab) {
    console.log('\nGoogle OAuth page detected - may need account selection...');
    const c2 = await connect(googleTab.webSocketDebuggerUrl);
    const googleText = await c2.ev(`document.body.innerText.substring(0, 500)`);
    console.log('Google page:', googleText.substring(0, 300));

    // Try to click the first Google account
    const accountClick = await c2.ev(`
      (() => {
        var els = document.querySelectorAll('[data-email], [data-identifier], .JDAKTe');
        if (els.length > 0) {
          els[0].click();
          return 'Clicked first account';
        }
        // Try clicking any visible email link
        var divs = document.querySelectorAll('div[role="link"], li[role="presentation"]');
        for (var i = 0; i < divs.length; i++) {
          if (divs[i].offsetParent) {
            divs[i].click();
            return 'Clicked: ' + divs[i].textContent.trim().substring(0, 50);
          }
        }
        return 'no account to click';
      })()
    `);
    console.log('Account:', accountClick);
    await sleep(5000);

    // Check result
    const allPages2 = await getPages();
    const gumDash = allPages2.find(p => p.url.includes('gumroad.com') && !p.url.includes('login'));
    if (gumDash) {
      console.log('Redirected to Gumroad!');
      const c3 = await connect(gumDash.webSocketDebuggerUrl);
      const t = await c3.ev(`document.body.innerText.substring(0, 500)`);
      console.log('Dashboard:', t.substring(0, 300));
      c3.close();
    }
    c2.close();
  } else {
    // Still on login page?
    const currentUrl = await c.ev('window.location.href');
    const currentText = await c.ev(`document.body.innerText.substring(0, 500)`);
    console.log('Still on:', currentUrl);
    console.log('Text:', currentText.substring(0, 300));
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
