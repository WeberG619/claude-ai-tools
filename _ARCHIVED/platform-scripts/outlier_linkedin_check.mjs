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

  // Find the active tab (LinkedIn or Outlier)
  const linkedinTab = tabs.find(t => t.type === "page" && t.url.includes("linkedin"));
  const outlierTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
  const target = outlierTab || linkedinTab || tabs.find(t => t.type === "page");

  if (!target) { console.log("No tab found"); return; }

  const match = target.url.includes("outlier") ? "outlier" : target.url.includes("linkedin") ? "linkedin" : target.url.substring(8, 30);
  let { ws, send, eval_ } = await connectToPage(match);

  let r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // If on Outlier skill selection, check Import and Review
  if (r.includes("Import and Review") || r.includes("Import skills")) {
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Import and Review'));
      if (btn) return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), disabled: btn.disabled });
      return 'not found';
    `);
    console.log("\nImport and Review:", r);

    // If enabled, click it
    const info = JSON.parse(r !== 'not found' ? r : '{"disabled":true}');
    if (!info.disabled) {
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('Import and Review'));
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return 'not found';
      `);
      if (r !== 'not found') {
        const pos = JSON.parse(r);
        await clickAt(send, pos.x, pos.y);
        console.log("Clicked Import and Review!");
        await sleep(5000);
        r = await eval_(`return window.location.href`);
        console.log("\nNew URL:", r);
        r = await eval_(`return document.body.innerText.substring(0, 5000)`);
        console.log("\nNew Page:", r);
      }
    }
  }

  // If on LinkedIn auth/consent page, check for Allow button
  if (r.includes("Allow") || r.includes("consent") || r.includes("authorize")) {
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Allow'));
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return 'not found';
    `);
    console.log("\nAllow button:", r);
    if (r !== 'not found') {
      const pos = JSON.parse(r);
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Allow");
      await sleep(5000);
      r = await eval_(`return window.location.href`);
      console.log("\nAfter allow URL:", r);
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
