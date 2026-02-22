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
  let { ws, send, eval_ } = await connectToPage("app.dataannotation");

  // Find and click the checkbox for terms agreement
  let r = await eval_(`
    const checkbox = document.querySelector('input[type="checkbox"]');
    if (checkbox) {
      const rect = checkbox.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), checked: checkbox.checked });
    }
    // Try label or div with checkbox role
    const label = Array.from(document.querySelectorAll('label, [role="checkbox"]'))
      .find(el => el.textContent.includes('agree') || el.textContent.includes('Terms'));
    if (label) {
      const rect = label.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 12), y: Math.round(rect.y + rect.height/2), type: 'label' });
    }
    return 'not found';
  `);
  console.log("Checkbox:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (!pos.checked) {
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked checkbox");
      await sleep(500);
    }
  }

  // Find and click Continue button
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, input[type="submit"], a'))
      .find(el => el.textContent?.trim() === 'Continue' || el.value === 'Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: btn.textContent?.trim() || btn.value });
    }
    return 'not found';
  `);
  console.log("Continue button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Continue");

    await sleep(8000);

    // Check where we are
    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
