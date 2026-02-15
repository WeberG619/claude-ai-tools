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
  let { ws, send, eval_ } = await connectToPage("outlier.ai");

  // Click "View Opportunities" or "Login" to start
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a, button'))
      .filter(el => el.offsetParent !== null)
      .filter(el => {
        const t = el.textContent.toLowerCase();
        return t.includes('view opportunities') || t.includes('sign up') || t.includes('apply') || t.includes('get started');
      })
      .map(el => ({ text: el.textContent.trim(), href: el.href || '', tag: el.tagName }));
    return JSON.stringify(links);
  `);
  console.log("Action links:", r);

  const links = JSON.parse(r);
  // Click the first "View Opportunities" link
  const viewOpp = links.find(l => l.text.toLowerCase().includes('view opportunities'));
  if (viewOpp && viewOpp.href) {
    await eval_(`window.location.href = '${viewOpp.href}'`);
  } else {
    // Try clicking the button directly
    await eval_(`
      const btn = Array.from(document.querySelectorAll('a, button'))
        .find(el => el.textContent.toLowerCase().includes('view opportunities') && el.offsetParent !== null);
      if (btn) btn.click();
    `);
  }
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("outlier"));

  r = await eval_(`return window.location.href`);
  console.log("\nNew URL:", r);

  r = await eval_(`
    const body = document.body.innerText;
    return body.substring(0, 6000);
  `);
  console.log("\nPage content:");
  console.log(r);

  // Look for sign up / apply buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('a, button'))
      .filter(el => el.offsetParent !== null)
      .filter(el => {
        const t = el.textContent.toLowerCase();
        return t.includes('sign') || t.includes('apply') || t.includes('register') || t.includes('google') || t.includes('create') || t.includes('join');
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 60),
        href: el.href || '',
        tag: el.tagName,
        rect: JSON.parse(JSON.stringify(el.getBoundingClientRect()))
      }));
    return JSON.stringify(btns, null, 2);
  `);
  console.log("\nSign up buttons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
