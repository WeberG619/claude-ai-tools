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
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Click on the English Writing opportunity
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a, [role="link"], [role="button"], div, span'))
      .filter(el => el.offsetParent !== null)
      .find(el => el.textContent.includes('English Writing and Content Reviewing'));
    if (links) {
      links.click();
      return 'clicked: ' + links.textContent.trim().substring(0, 80);
    }
    return 'not found';
  `);
  console.log("Click result:", r);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("outlier"));

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);

  r = await eval_(`
    const body = document.body.innerText;
    return body.substring(0, 6000);
  `);
  console.log("\nPage content:");
  console.log(r);

  // Look for apply/sign up buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('a, button'))
      .filter(el => el.offsetParent !== null)
      .filter(el => {
        const t = el.textContent.toLowerCase().trim();
        return t.length > 0 && t.length < 40 && (
          t.includes('apply') || t.includes('sign') || t.includes('start') ||
          t.includes('google') || t.includes('register') || t.includes('join') ||
          t.includes('create') || t.includes('get started')
        );
      })
      .map(el => ({
        text: el.textContent.trim(),
        href: el.href || '',
        tag: el.tagName,
        rect: JSON.parse(JSON.stringify(el.getBoundingClientRect()))
      }));
    return JSON.stringify(btns, null, 2);
  `);
  console.log("\nAction buttons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
