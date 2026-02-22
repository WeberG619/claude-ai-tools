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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("Tabs:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

  const daTab = tabs.find(t => t.type === "page" && t.url.includes("dataannotation"));
  if (!daTab) { console.log("No DataAnnotation tab found"); return; }

  let { ws, send, eval_ } = await connectToPage("dataannotation");

  let r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);

  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Check for any buttons or links to proceed
  r = await eval_(`
    const els = Array.from(document.querySelectorAll('button, a, input[type="submit"]'));
    return JSON.stringify(els.filter(el => el.offsetParent !== null).map(el => ({
      tag: el.tagName,
      text: (el.textContent?.trim() || el.value || '').substring(0, 60),
      href: el.href || ''
    })).filter(e => e.text));
  `);
  console.log("\nClickable elements:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
