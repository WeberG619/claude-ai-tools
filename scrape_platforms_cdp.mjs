// Raw CDP WebSocket - scrape Upwork & Fiverr via Chrome DevTools Protocol
// Node 22+ native WebSocket + fetch, zero dependencies

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
    const nav = async (url) => { await send('Page.navigate', { url }); await sleep(4000); };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  console.log('Connecting to Chrome CDP on port 9222...');
  let pages = await getPages();
  console.log(`${pages.length} tab(s) open`);
  pages.forEach((p, i) => console.log(`  ${i + 1}. ${p.title.substring(0, 50)} | ${p.url.substring(0, 80)}`));

  // Use first page
  const tab = pages[0];
  const c = await connect(tab.webSocketDebuggerUrl);
  console.log('WebSocket connected\n');

  // Navigate to Upwork
  await c.nav('https://www.upwork.com/nx/find-work/best-matches');
  await sleep(2000);
  let url = await c.ev('location.href');
  console.log('URL: ' + url);

  if (url.includes('login') || url.includes('account-security')) {
    console.log('\n>>> UPWORK NEEDS LOGIN <<<');
    console.log('Please log in on the CDP Chrome window...');
    console.log('Waiting up to 90s...\n');
    for (let i = 0; i < 30; i++) {
      await sleep(3000);
      url = await c.ev('location.href');
      if (!url.includes('login') && !url.includes('account-security')) {
        console.log('Login successful!');
        await sleep(3000);
        break;
      }
      if (i % 5 === 0 && i > 0) console.log(`  Waiting... ${i * 3}s`);
    }
  }

  if (url.includes('login')) {
    console.log('Still not logged in. Skipping Upwork.');
  } else {
    // ===== BEST MATCHES =====
    console.log('\n======= UPWORK BEST MATCHES =======');
    await c.nav('https://www.upwork.com/nx/find-work/best-matches');
    await sleep(3000);
    let text = await c.ev('document.body.innerText.substring(0, 5000)');
    console.log(text);

    // ===== REVIT SEARCH =====
    console.log('\n\n======= UPWORK REVIT/BIM JOBS (Recent) =======');
    await c.nav('https://www.upwork.com/nx/search/jobs/?q=revit+BIM&sort=recency&payment_verified=1');
    await sleep(3000);
    text = await c.ev('document.body.innerText.substring(0, 5000)');
    console.log(text);

    // ===== CONNECTS =====
    console.log('\n\n======= UPWORK CONNECTS =======');
    await c.nav('https://www.upwork.com/nx/plans/connects/');
    await sleep(3000);
    text = await c.ev('document.body.innerText.substring(0, 2000)');
    console.log(text);
  }

  c.close();

  // ===== FIVERR =====
  console.log('\n\n======= FIVERR GIGS =======');
  // Open new tab for Fiverr
  const fRes = await fetch(`${CDP}/json/new?https://www.fiverr.com/users/weberg619/manage_gigs`);
  const fTab = await fRes.json();
  await sleep(5000);
  // Re-fetch pages to get the new tab's WS url
  pages = await getPages();
  const fPage = pages.find(p => p.url.includes('fiverr.com'));
  if (fPage) {
    const fc = await connect(fPage.webSocketDebuggerUrl);
    await sleep(2000);
    const fUrl = await fc.ev('location.href');
    if (fUrl.includes('login') || fUrl.includes('join')) {
      console.log('FIVERR: Not logged in on CDP Chrome.');
      console.log('Please log in, then re-run this script.');
    } else {
      console.log('URL: ' + fUrl);
      let fText = await fc.ev('document.body.innerText.substring(0, 3000)');
      console.log(fText);

      // Briefs
      console.log('\n--- FIVERR BRIEFS ---');
      await fc.nav('https://www.fiverr.com/users/weberg619/briefs');
      await sleep(3000);
      fText = await fc.ev('document.body.innerText.substring(0, 2000)');
      console.log(fText);
    }
    fc.close();
  }

  console.log('\n======= DONE =======');
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
