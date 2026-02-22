// Check Fiverr state - navigate to gigs page
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  console.log("Open tabs:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 100)));

  // Find any page tab to use for navigation
  let tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com"));
  if (!tab) tab = tabs.find(t => t.type === "page" && t.url.includes("upwork.com"));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab found"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r));
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Navigate to Fiverr gigs management
  await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/manage_gigs'`);
  await sleep(6000);
  ws.close(); await sleep(1000);

  // Reconnect
  const tabs2 = await (await fetch(CDP_HTTP + "/json")).json();
  const tab2 = tabs2.find(t => t.type === "page" && t.url.includes("fiverr.com"));
  if (!tab2) { console.log("No Fiverr tab after nav"); return; }

  const ws2 = new WebSocket(tab2.webSocketDebuggerUrl);
  await new Promise(r => ws2.addEventListener("open", r));
  const pending2 = new Map();
  let id2 = 1;
  ws2.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending2.has(m.id)) {
      const p = pending2.get(m.id);
      pending2.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const eval2 = async (expr) => {
    const i = id2++;
    const r = await new Promise((res, rej) => {
      pending2.set(i, { res, rej });
      ws2.send(JSON.stringify({ id: i, method: "Runtime.evaluate", params: {
        expression: `(async () => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      }}));
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  let r = await eval2(`return window.location.href`);
  console.log("\nURL:", r);

  r = await eval2(`
    const main = document.querySelector('main') || document.body;
    return main.innerText.substring(0, 5000);
  `);
  console.log("\nPage content:");
  console.log(r);

  ws2.close();
})().catch(e => console.error("Error:", e.message));
