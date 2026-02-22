// Deep check Upwork profile edit pages via CDP
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

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  const c = await connect(tab.webSocketDebuggerUrl);

  // 1. Main profile edit page
  console.log('======= PROFILE EDIT =======');
  await c.nav('https://www.upwork.com/freelancers/settings/profile/edit');
  await sleep(2000);
  let text = await c.ev('document.body.innerText.substring(0, 8000)');
  console.log(text);

  // Scroll for more
  await c.ev('window.scrollTo(0, 3000)');
  await sleep(1000);
  let text2 = await c.ev('document.body.innerText.substring(8000, 16000)');
  console.log(text2);

  // 2. Find work page for warnings
  console.log('\n\n======= FIND WORK (warnings?) =======');
  await c.nav('https://www.upwork.com/nx/find-work/best-matches');
  await sleep(3000);
  text = await c.ev('document.body.innerText.substring(0, 5000)');
  console.log(text);

  // 3. Membership & connects
  console.log('\n\n======= MEMBERSHIP & CONNECTS =======');
  await c.nav('https://www.upwork.com/freelancers/settings/membershipAndConnects');
  await sleep(2000);
  text = await c.ev('document.body.innerText.substring(0, 3000)');
  console.log(text);

  // 4. Check hourly rate setting
  console.log('\n\n======= RATE & AVAILABILITY =======');
  await c.nav('https://www.upwork.com/freelancers/settings/profile');
  await sleep(2000);
  await c.ev('window.scrollTo(0, 1000)');
  await sleep(500);
  text = await c.ev('document.body.innerText.substring(0, 6000)');
  console.log(text);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
