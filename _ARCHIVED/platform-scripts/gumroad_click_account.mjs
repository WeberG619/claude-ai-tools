// Click the Google account to complete Gumroad OAuth
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

  // Find Google OAuth tab
  const googleTab = pages.find(p => p.url.includes('accounts.google.com'));
  if (!googleTab) { console.log('No Google OAuth tab found'); process.exit(1); }

  console.log('Google tab:', googleTab.url.substring(0, 80));
  const c = await connect(googleTab.webSocketDebuggerUrl);
  await sleep(500);

  // Get the page text
  const text = await c.ev(`document.body.innerText`);
  console.log('Page text:', text.substring(0, 300));

  // Click the account (Weber Gouin / weber@bimopsstudio.com)
  console.log('\nClicking account...');
  const clicked = await c.ev(`
    (() => {
      // Try data-identifier or data-email attributes
      var els = document.querySelectorAll('[data-email], [data-identifier]');
      for (var i = 0; i < els.length; i++) {
        els[i].click();
        return 'Clicked data-email: ' + (els[i].getAttribute('data-email') || els[i].getAttribute('data-identifier'));
      }
      // Try li elements in the account list
      var lis = document.querySelectorAll('li');
      for (var i = 0; i < lis.length; i++) {
        if (lis[i].textContent.includes('Weber') || lis[i].textContent.includes('bimops')) {
          lis[i].click();
          return 'Clicked li: ' + lis[i].textContent.trim().substring(0, 50);
        }
      }
      // Try div[role="link"] or button
      var divs = document.querySelectorAll('div[role="link"], [data-authuser]');
      for (var i = 0; i < divs.length; i++) {
        if (divs[i].textContent.includes('Weber') || divs[i].textContent.includes('bimops')) {
          divs[i].click();
          return 'Clicked: ' + divs[i].textContent.trim().substring(0, 50);
        }
      }
      // Brute force - click any element with the email
      var all = document.querySelectorAll('*');
      for (var i = 0; i < all.length; i++) {
        if (all[i].children.length === 0 && all[i].textContent.includes('bimops')) {
          // Click its parent
          all[i].closest('[role], a, button, li, div[tabindex]')?.click();
          return 'Clicked parent of: ' + all[i].textContent.trim();
        }
      }
      return 'not found';
    })()
  `);
  console.log('Result:', clicked);
  await sleep(8000);

  // Check if we got redirected back to Gumroad
  const allPages = await getPages();
  console.log('\n=== ALL TABS ===');
  for (const p of allPages) {
    console.log(' -', p.url.substring(0, 100));
  }

  const gumTab = allPages.find(p => p.url.includes('gumroad.com') && !p.url.includes('login'));
  if (gumTab) {
    console.log('\nGumroad found!');
    const c2 = await connect(gumTab.webSocketDebuggerUrl);
    const dashUrl = await c2.ev('window.location.href');
    const dashText = await c2.ev(`document.body.innerText.substring(0, 1000)`);
    console.log('URL:', dashUrl);
    console.log('Dashboard:', dashText.substring(0, 500));
    c2.close();
  } else {
    // Check if the google tab changed
    const remainingGoogle = allPages.find(p => p.url.includes('accounts.google.com'));
    if (remainingGoogle) {
      const c2 = await connect(remainingGoogle.webSocketDebuggerUrl);
      const gUrl = await c2.ev('window.location.href');
      const gText = await c2.ev(`document.body.innerText.substring(0, 500)`);
      console.log('Still on Google:', gUrl.substring(0, 80));
      console.log('Text:', gText.substring(0, 300));
      c2.close();
    }
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
