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

  // Scroll Continue button into view and get its position
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'instant', block: 'center' });
      await new Promise(r => setTimeout(r, 500));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
    }
    return 'not found';
  `);
  console.log("Continue after scroll:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (pos.x > 0 && pos.y > 0) {
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Continue at", pos.x, pos.y);
    } else {
      // Try submitting the form via JS
      console.log("Button still offscreen, submitting form via JS");
      r = await eval_(`
        const form = document.querySelector('form');
        if (form) { form.submit(); return 'submitted'; }
        return 'no form';
      `);
      console.log("Form submit:", r);
    }

    await sleep(10000);
    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage:", r);

    // Check for errors
    r = await eval_(`
      const text = document.body.innerText;
      const lines = text.split('\\n').filter(l => l.trim().length > 0);
      return JSON.stringify(lines.filter(l =>
        l.toLowerCase().includes('error') || l.toLowerCase().includes('invalid') ||
        l.toLowerCase().includes('please') || l.toLowerCase().includes('required') ||
        l.toLowerCase().includes('taken') || l.toLowerCase().includes('already') ||
        l.toLowerCase().includes('confirm')
      ).slice(0, 10));
    `);
    console.log("\nMessages:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
