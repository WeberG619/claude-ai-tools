// Check current Upwork page state
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found matching "${urlMatch}"`);
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
  // List all upwork tabs
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const upworkTabs = tabs.filter(t => t.type === "page" && t.url.includes("upwork"));
  console.log("Upwork tabs:", upworkTabs.map(t => t.url));

  if (upworkTabs.length === 0) {
    console.log("No Upwork tabs found!");
    return;
  }

  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Get URL and page content
  let r = await eval_(`return JSON.stringify({
    url: location.href,
    title: document.title,
    bodyText: document.body.innerText.substring(0, 1500)
  })`);
  const page = JSON.parse(r);
  console.log("URL:", page.url);
  console.log("Title:", page.title);
  console.log("\nBody text:");
  console.log(page.bodyText);

  // All visible inputs
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, type: el.type,
        placeholder: el.placeholder || '',
        value: el.value,
        name: el.name || ''
      }));
    return JSON.stringify(inputs, null, 2);
  `);
  console.log("\nVisible inputs:", r);

  // All visible buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 50));
    return JSON.stringify(btns);
  `);
  console.log("\nVisible buttons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
