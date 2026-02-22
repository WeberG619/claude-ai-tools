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

  // Click Continue
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Continue'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Continue button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Continue");
    await sleep(10000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage:", r);

    // Check for errors
    r = await eval_(`
      const text = document.body.innerText;
      const lines = text.split('\\n').filter(l => l.trim().length > 0);
      return JSON.stringify(lines.filter(l =>
        l.toLowerCase().includes('error') || l.toLowerCase().includes('short') ||
        l.toLowerCase().includes('invalid') || l.toLowerCase().includes('please') ||
        l.toLowerCase().includes('taken') || l.toLowerCase().includes('already')
      ));
    `);
    console.log("\nError lines:", r);

    // Check form fields if still on a form
    r = await eval_(`
      const inputs = document.querySelectorAll('input, select, textarea');
      return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
        type: i.type, name: i.name, id: i.id, placeholder: i.placeholder?.substring(0, 40),
        options: i.tagName === 'SELECT' ? Array.from(i.options).slice(0, 10).map(o => o.text.substring(0, 30)) : undefined
      })));
    `);
    console.log("\nForm fields:", r);

    // Check buttons
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button, input[type="submit"]'))
        .filter(b => b.offsetParent !== null);
      return JSON.stringify(btns.map(b => ({
        text: (b.textContent?.trim() || b.value || '').substring(0, 40),
        rect: (() => { const r = b.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
      })));
    `);
    console.log("\nButtons:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
