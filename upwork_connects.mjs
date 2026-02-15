const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  // Use the Fiverr tab
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (!tab) { console.log("No tab available"); return; }

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

  // Navigate to Upwork
  await send("Page.navigate", { url: "https://www.upwork.com/nx/find-work/best-matches" });
  await sleep(8000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Check if logged in
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage:", r);

  // Look for Connects info
  r = await eval_(`
    const text = document.body.innerText;
    const connectsMatch = text.match(/(\\d+)\\s*(?:Available\\s*)?Connects/i);
    if (connectsMatch) return 'Connects found: ' + connectsMatch[0];
    // Look for connects in any element
    const all = document.querySelectorAll('*');
    for (const el of all) {
      if (el.children.length === 0 && el.textContent.toLowerCase().includes('connect')) {
        return 'Connect text: ' + el.textContent.trim().substring(0, 80);
      }
    }
    return 'no connects info found';
  `);
  console.log("\nConnects:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
