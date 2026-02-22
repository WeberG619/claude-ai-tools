const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");

  // Navigate to buy connects page
  await eval_(`window.location.href = 'https://www.upwork.com/nx/plans/connects/'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Check the page
  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  r = await eval_(`
    const main = document.querySelector('main') || document.body;
    return main.innerText.substring(0, 5000);
  `);
  console.log("\\nPage content:");
  console.log(r);

  // Look for buy connects options / buttons
  r = await eval_(`
    const buttons = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null)
      .filter(el => {
        const t = el.textContent.toLowerCase();
        return t.includes('buy') || t.includes('connect') || t.includes('purchase') || t.includes('add');
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 80),
        href: el.href || '',
        rect: el.getBoundingClientRect()
      }));
    return JSON.stringify(buttons, null, 2);
  `);
  console.log("\\nRelevant buttons:");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
