// Check status of submitted proposals
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

  // Navigate to proposals page
  console.log('=== NAVIGATING TO PROPOSALS ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/proposals/submitted'`);
  await sleep(5000);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Get full page content
  const pageText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 6000)`);
  console.log('\n=== PROPOSALS ===');
  console.log(pageText);

  // Check for any messages/interviews
  console.log('\n=== CHECKING MESSAGES ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/ab/messages'`);
  await sleep(5000);

  const msgUrl = await c.ev('window.location.href');
  console.log('Messages URL:', msgUrl);

  const msgText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 3000)`);
  console.log(msgText);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
