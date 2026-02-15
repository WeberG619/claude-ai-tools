const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  console.log("All tabs:");
  tabs.filter(t => t.type === "page").forEach((t, i) => console.log(`  ${i}: ${t.url.substring(0, 140)}`));

  const tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tabs"); return; }

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
  const eval_ = async (expr) => {
    const i = id++;
    const r = await new Promise((res, rej) => {
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method: "Runtime.evaluate", params: {
        expression: `(async () => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      }}));
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  let r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage content:");
  console.log(r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
