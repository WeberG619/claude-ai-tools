// Handle Fiverr identity verification and publish
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Click Verify link
  let r = await eval_(`
    const link = Array.from(document.querySelectorAll('a, button, span'))
      .find(el => el.textContent.trim() === 'Verify');
    if (link) {
      link.click();
      return JSON.stringify({ clicked: true, href: link.href || '', tag: link.tagName });
    }
    return JSON.stringify({ clicked: false });
  `);
  console.log("Verify click:", r);
  await sleep(5000);

  // Check what page we're on
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  const page = JSON.parse(r);
  console.log("URL:", page.url);
  console.log("\nBody:", page.bodyPreview);

  // Inspect form fields
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 40),
        value: (el.value || '').substring(0, 40),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y)
      }));

    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        y: Math.round(el.getBoundingClientRect().y)
      }))
      .filter(b => b.text.length > 0);

    return JSON.stringify({ inputs, btns: btns.slice(0, 10) });
  `);
  console.log("\nForm elements:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
