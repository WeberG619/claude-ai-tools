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

async function typeText(send, text) {
  for (const ch of text) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", text: ch });
    await send("Input.dispatchKeyEvent", { type: "keyUp", text: ch });
    await sleep(30);
  }
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Click "Connect Personal Website"
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Connect Personal Website'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Website button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Connect Personal Website");
    await sleep(1500);

    // Check for input field
    r = await eval_(`
      const inputs = document.querySelectorAll('input[type="text"], input[type="url"], input:not([type="hidden"]):not([type="file"]):not([type="radio"]):not([type="checkbox"])');
      return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
        placeholder: i.placeholder,
        type: i.type,
        value: i.value
      })));
    `);
    console.log("Inputs:", r);

    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage:", r);

    // Try to find and fill URL input
    r = await eval_(`
      const inputs = document.querySelectorAll('input');
      for (const inp of inputs) {
        if (inp.offsetParent !== null && (inp.type === 'url' || inp.type === 'text' || inp.type === '') && inp.placeholder?.toLowerCase().includes('url')) {
          const rect = inp.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), placeholder: inp.placeholder });
        }
      }
      // Try any visible text input
      for (const inp of inputs) {
        if (inp.offsetParent !== null && (inp.type === 'url' || inp.type === 'text' || inp.type === '') && !inp.name?.includes('file')) {
          const rect = inp.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), placeholder: inp.placeholder || 'none' });
        }
      }
      return 'not found';
    `);
    console.log("\nURL input:", r);

    if (r !== 'not found') {
      const iPos = JSON.parse(r);
      await clickAt(send, iPos.x, iPos.y);
      await sleep(200);
      await typeText(send, "https://bimopsstudio.com");
      console.log("Typed website URL");
      await sleep(500);

      // Look for submit/save button
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button'));
        return JSON.stringify(btns.filter(b => b.offsetParent !== null).map(b => ({
          text: b.textContent.trim().substring(0, 60),
          disabled: b.disabled
        })));
      `);
      console.log("\nButtons after URL:", r);
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
