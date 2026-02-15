const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const res = await fetch(`${CDP}/json`);
  const tabs = await res.json();
  const page = tabs.find(t => t.type === 'page' && t.url.includes('upwork.com'));
  if (!page) { console.log('No Upwork tab'); process.exit(1); }

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));

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
  const ev = async (expr) => {
    const r = await new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
    });
    return r.result?.value;
  };

  // Get full page text to see skills editor state
  const text = await ev('document.body.innerText.substring(0, 8000)');
  console.log(text);

  ws.close();
  process.exit(0);
}
main().catch(e => { console.error(e.message); process.exit(1); });
