const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No Clickworker tab"); return; }

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

  // Fix gender - get select options
  let r = await eval_(`
    const sel = document.querySelector('#user_gender');
    if (sel) {
      const opts = Array.from(sel.options).map(o => ({ value: o.value, text: o.text }));
      return JSON.stringify(opts);
    }
    return 'not found';
  `);
  console.log("Gender options:", r);

  // Set using the correct option value
  const opts = JSON.parse(r);
  const maleOpt = opts.find(o => o.text.includes('Male'));
  if (maleOpt) {
    r = await eval_(`
      const sel = document.querySelector('#user_gender');
      sel.value = '${maleOpt.value}';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set: ' + sel.value + ' (' + sel.options[sel.selectedIndex].text + ')';
    `);
    console.log("Gender set:", r);
  }

  // Also click on the select to trigger any JS handlers
  r = await eval_(`
    const sel = document.querySelector('#user_gender');
    const rect = sel.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
  `);
  const selPos = JSON.parse(r);
  await clickAt(send, selPos.x, selPos.y);
  await sleep(300);

  // Select Male option via keyboard
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "m", code: "KeyM", text: "m" });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "m", code: "KeyM" });
  await sleep(300);

  // Click away
  await clickAt(send, selPos.x, selPos.y + 100);
  await sleep(300);

  // Verify
  r = await eval_(`
    const sel = document.querySelector('#user_gender');
    return sel ? sel.options[sel.selectedIndex].text : 'N/A';
  `);
  console.log("Gender now:", r);

  console.log("\n** Form is ready. Weber needs to: **");
  console.log("1. Set a password in both password fields");
  console.log("2. Click Continue");

  ws.close();
})().catch(e => console.error("Error:", e.message));
