// CDP scraper - all freelance platforms
// Node 22+ native WebSocket + fetch

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
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function scrapeTab(pages, urlMatch) {
  const tab = pages.find(p => p.url.includes(urlMatch));
  if (!tab) return null;
  return await connect(tab.webSocketDebuggerUrl);
}

async function main() {
  console.log('CDP connecting...');
  let pages = await getPages();
  console.log(`${pages.length} tabs found\n`);

  // =================== FIVERR ===================
  console.log('======================================');
  console.log('  FIVERR - Gigs & Dashboard');
  console.log('======================================');
  let c = await scrapeTab(pages, 'fiverr.com');
  if (c) {
    await c.nav('https://www.fiverr.com/users/weberg619/manage_gigs');
    await sleep(2000);
    let text = await c.ev('document.body.innerText.substring(0, 4000)');
    console.log(text);

    console.log('\n--- FIVERR ORDERS/DASHBOARD ---');
    await c.nav('https://www.fiverr.com/users/weberg619/manage_orders');
    await sleep(2000);
    text = await c.ev('document.body.innerText.substring(0, 2000)');
    console.log(text);

    console.log('\n--- FIVERR BUYER REQUESTS / BRIEFS ---');
    await c.nav('https://www.fiverr.com/users/weberg619/briefs');
    await sleep(2000);
    text = await c.ev('document.body.innerText.substring(0, 2000)');
    console.log(text);

    console.log('\n--- FIVERR INBOX ---');
    await c.nav('https://www.fiverr.com/inbox');
    await sleep(2000);
    text = await c.ev('document.body.innerText.substring(0, 2000)');
    console.log(text);
    c.close();
  } else {
    console.log('No Fiverr tab found');
  }

  // =================== UPWORK ===================
  console.log('\n\n======================================');
  console.log('  UPWORK - Jobs & Connects');
  console.log('======================================');
  // Use any available tab to navigate to Upwork
  const dataTab = pages.find(p => p.url.includes('data:') || p.url === 'about:blank') || pages[1];
  if (dataTab) {
    c = await connect(dataTab.webSocketDebuggerUrl);

    // Best matches
    await c.nav('https://www.upwork.com/nx/find-work/best-matches');
    await sleep(3000);
    let url = await c.ev('location.href');
    if (url.includes('login')) {
      console.log('NOT LOGGED IN to Upwork');
    } else {
      let text = await c.ev('document.body.innerText.substring(0, 6000)');
      console.log('--- BEST MATCHES ---');
      console.log(text);

      // Connects
      console.log('\n--- CONNECTS ---');
      await c.nav('https://www.upwork.com/nx/plans/connects/');
      await sleep(2000);
      text = await c.ev('document.body.innerText.substring(0, 2000)');
      console.log(text);

      // Revit/BIM search
      console.log('\n--- REVIT/BIM JOBS (Recent) ---');
      await c.nav('https://www.upwork.com/nx/search/jobs/?q=revit+BIM&sort=recency&payment_verified=1');
      await sleep(3000);
      text = await c.ev('document.body.innerText.substring(0, 5000)');
      console.log(text);

      // Also search construction docs
      console.log('\n--- CONSTRUCTION DOCUMENTS JOBS ---');
      await c.nav('https://www.upwork.com/nx/search/jobs/?q=construction+documents+architectural&sort=recency&payment_verified=1');
      await sleep(3000);
      text = await c.ev('document.body.innerText.substring(0, 5000)');
      console.log(text);

      // My proposals
      console.log('\n--- MY PROPOSALS ---');
      await c.nav('https://www.upwork.com/nx/proposals/');
      await sleep(2000);
      text = await c.ev('document.body.innerText.substring(0, 2000)');
      console.log(text);
    }
    c.close();
  }

  // =================== FREELANCER ===================
  console.log('\n\n======================================');
  console.log('  FREELANCER.COM');
  console.log('======================================');
  c = await scrapeTab(pages, 'freelancer.com');
  if (c) {
    await c.nav('https://www.freelancer.com/dashboard');
    await sleep(3000);
    let text = await c.ev('document.body.innerText.substring(0, 3000)');
    console.log('--- DASHBOARD ---');
    console.log(text);

    // Search Revit jobs
    console.log('\n--- REVIT JOBS ---');
    await c.nav('https://www.freelancer.com/jobs/revit/');
    await sleep(3000);
    text = await c.ev('document.body.innerText.substring(0, 4000)');
    console.log(text);
    c.close();
  } else {
    console.log('No Freelancer tab found');
  }

  // =================== PEOPLEPERHOUR ===================
  console.log('\n\n======================================');
  console.log('  PEOPLEPERHOUR');
  console.log('======================================');
  c = await scrapeTab(pages, 'peopleperhour.com');
  if (c) {
    await c.nav('https://www.peopleperhour.com/dashboard/seller');
    await sleep(3000);
    let text = await c.ev('document.body.innerText.substring(0, 3000)');
    console.log('--- SELLER DASHBOARD ---');
    console.log(text);

    // Browse jobs
    console.log('\n--- REVIT/BIM JOBS ---');
    await c.nav('https://www.peopleperhour.com/freelance-jobs?keyword=revit+BIM');
    await sleep(3000);
    text = await c.ev('document.body.innerText.substring(0, 4000)');
    console.log(text);
    c.close();
  } else {
    console.log('No PeoplePerHour tab found');
  }

  console.log('\n\n======= ALL PLATFORMS SCRAPED =======');
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
