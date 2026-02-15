// Upwork languages - select English proficiency and continue
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
      expression: `(() => { ${expr} })()`,
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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Click the proficiency dropdown (role="combobox" at ~751,341)
  let r = await eval_(`
    const combo = document.querySelector('[role="combobox"]');
    if (combo) {
      const rect = combo.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no combobox' });
  `);
  console.log("Combobox:", r);
  const combo = JSON.parse(r);

  if (!combo.error) {
    await clickAt(send, combo.x, combo.y);
    await sleep(800);

    // Find dropdown options
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[role="option"], [class*="dropdown-item"], [class*="dropdown-menu"] li, ul[class*="list"] li'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    console.log("Dropdown options:", r);
    const opts = JSON.parse(r);

    // Select "Native or Bilingual" or the highest proficiency
    const native = opts.find(o => o.text.includes('Native') || o.text.includes('Bilingual') || o.text.includes('Fluent'));
    if (native) {
      await clickAt(send, native.x, native.y);
      console.log(`Selected: ${native.text}`);
    } else if (opts.length > 0) {
      // Select last option (typically highest)
      const last = opts[opts.length - 1];
      await clickAt(send, last.x, last.y);
      console.log(`Selected: ${last.text}`);
    }
    await sleep(1000);

    // Check validation cleared
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 80));
      return JSON.stringify(errors);
    `);
    console.log("Errors after selection:", r);
  }

  // Click Next
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next') && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next' });
  `);
  const next = JSON.parse(r);
  if (!next.error) {
    await clickAt(send, next.x, next.y);
    console.log("Clicked Next");
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 300) })`);
    console.log("\nNext page:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
