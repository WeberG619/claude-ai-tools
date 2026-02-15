const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
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
  return { ws, send, eval_ };
}

(async () => {
  // Check if Fiverr tab exists
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("Open tabs:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 100)));

  let fiverrTab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));

  if (!fiverrTab) {
    // Navigate an existing tab to Fiverr profile settings
    // Use the DataAnnotation tab since we're done with it
    const daTab = tabs.find(t => t.type === "page" && t.url.includes("dataannotation"));
    const targetTab = daTab || tabs.find(t => t.type === "page" && !t.url.includes("outlier"));

    if (!targetTab) { console.log("No available tab to navigate"); return; }

    const ws = new WebSocket(targetTab.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
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

    await send("Page.navigate", { url: "https://www.fiverr.com/settings/profile" });
    console.log("Navigating to Fiverr profile settings...");
    await sleep(8000);

    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", {
        expression: `(async () => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    let r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage:", r);

    ws.close();
  } else {
    let { ws, send, eval_ } = await connectToPage("fiverr");
    await send("Page.navigate", { url: "https://www.fiverr.com/settings/profile" });
    await sleep(8000);

    let r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage:", r);

    ws.close();
  }
})().catch(e => console.error("Error:", e.message));
