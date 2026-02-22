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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Find ANY element with "APPLY" text
  let r = await eval_(`
    const els = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const t = el.textContent.trim();
        return t === 'APPLY NOW' && el.children.length === 0 && el.offsetParent !== null;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        class: (el.className || '').substring(0, 80),
        rect: JSON.parse(JSON.stringify(el.getBoundingClientRect())),
        parent: el.parentElement?.tagName,
        parentClass: (el.parentElement?.className || '').substring(0, 80),
        parentHref: el.parentElement?.href || ''
      }));
    return JSON.stringify(els, null, 2);
  `);
  console.log("APPLY NOW elements:");
  console.log(r);

  const els = JSON.parse(r);
  if (els.length > 0) {
    // Scroll to and click the first one
    const el = els[0];
    await eval_(`
      const applyEl = Array.from(document.querySelectorAll('*'))
        .filter(el => el.textContent.trim() === 'APPLY NOW' && el.children.length === 0 && el.offsetParent !== null)[0];
      applyEl.scrollIntoView({ block: 'center' });
    `);
    await sleep(500);

    // Get fresh coords
    r = await eval_(`
      const applyEl = Array.from(document.querySelectorAll('*'))
        .filter(el => el.textContent.trim() === 'APPLY NOW' && el.children.length === 0 && el.offsetParent !== null)[0];
      const rect = applyEl.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const pos = JSON.parse(r);
    console.log("\nClicking APPLY NOW at:", pos);
    await clickAt(send, pos.x, pos.y);
    await sleep(5000);

    // Check result
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("outlier"));

    r = await eval_(`return window.location.href`);
    console.log("\nNew URL:", r);

    r = await eval_(`
      const body = document.body.innerText;
      return body.substring(0, 5000);
    `);
    console.log("\nPage content:");
    console.log(r);
  } else {
    console.log("No APPLY NOW elements found - trying LOG IN instead");
    // Try clicking LOG IN
    r = await eval_(`
      const loginEl = Array.from(document.querySelectorAll('*'))
        .filter(el => el.textContent.trim() === 'LOG IN' && el.children.length === 0 && el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          rect: JSON.parse(JSON.stringify(el.getBoundingClientRect())),
          parent: el.parentElement?.tagName,
          parentHref: el.parentElement?.href || ''
        }));
      return JSON.stringify(loginEl, null, 2);
    `);
    console.log("\nLOG IN elements:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
