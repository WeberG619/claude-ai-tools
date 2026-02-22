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
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Check current checkbox states
  let r = await eval_(`
    const cbs = document.querySelectorAll('[role="checkbox"]');
    return JSON.stringify(Array.from(cbs).map(cb => ({
      checked: cb.getAttribute('aria-checked'),
      x: Math.round(cb.getBoundingClientRect().x + cb.getBoundingClientRect().width/2),
      y: Math.round(cb.getBoundingClientRect().y + cb.getBoundingClientRect().height/2)
    })));
  `);
  console.log("Checkbox states:", r);

  const cbs = JSON.parse(r);
  // Click any unchecked checkboxes
  for (const cb of cbs) {
    if (cb.checked !== 'true') {
      await clickAt(send, cb.x, cb.y);
      console.log(`Checked checkbox at (${cb.x}, ${cb.y})`);
      await sleep(300);
    } else {
      console.log(`Already checked at (${cb.x}, ${cb.y})`);
    }
  }

  await sleep(500);

  // Verify both are now checked
  r = await eval_(`
    const cbs = document.querySelectorAll('[role="checkbox"]');
    return JSON.stringify(Array.from(cbs).map(cb => cb.getAttribute('aria-checked')));
  `);
  console.log("\nCheckbox states after:", r);

  // Check Next button
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]'))
      .find(b => b.textContent.includes('Next'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({
        disabled: btn.disabled,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    return 'not found';
  `);
  console.log("Next button:", r);

  const nextInfo = JSON.parse(r !== 'not found' ? r : '{"disabled":true}');
  if (!nextInfo.disabled) {
    await clickAt(send, nextInfo.x, nextInfo.y);
    console.log("Clicked Next!");
    await sleep(8000);
    r = await eval_(`return window.location.href`);
    console.log("\nNew URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nNew Page:", r);
  } else {
    console.log("Next still disabled - checking what's needed...");
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
