// Navigate to Upwork signup in current browser
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  // Check all existing tabs
  let res = await fetch(`${CDP_HTTP}/json`);
  let tabs = await res.json();
  console.log("=== Current Tabs ===");
  for (const t of tabs) {
    if (t.type === "page") {
      console.log(`  ${t.title?.substring(0, 40)} | ${t.url.substring(0, 80)}`);
    }
  }

  // Find a tab to use - prefer an unused one or the Fiverr tab
  const fiverr = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com/users"));
  if (!fiverr) { console.log("No suitable tab"); return; }

  const ws = new WebSocket(fiverr.webSocketDebuggerUrl);
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

  // Navigate to Upwork signup
  console.log("\nNavigating to Upwork...");
  await eval_(`window.location.href = 'https://www.upwork.com/nx/signup/?dest=home'`);
  await sleep(8000);

  // Reconnect
  ws.close();
  await sleep(1000);

  res = await fetch(`${CDP_HTTP}/json`);
  tabs = await res.json();
  const upTab = tabs.find(t => t.type === "page" && t.url.includes("upwork.com"));
  if (!upTab) {
    console.log("Upwork tab not found!");
    // List all tabs
    for (const t of tabs) {
      if (t.type === "page") console.log(`  ${t.url.substring(0, 100)}`);
    }
    return;
  }

  const ws2 = new WebSocket(upTab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws2.addEventListener("open", res); ws2.addEventListener("error", rej); });
  const pending2 = new Map();
  let id2 = 1;
  ws2.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending2.has(msg.id)) {
      const p = pending2.get(msg.id);
      pending2.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send2 = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id2++;
    pending2.set(msgId, { res, rej });
    ws2.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval2 = async (expr) => {
    const r = await send2("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  let r = await eval2(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      body: document.body.innerText.substring(0, 800)
    });
  `);
  console.log("Upwork page:", r);

  ws2.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
