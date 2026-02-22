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

  // Find ALL buttons on page
  let r = await eval_(`
    const btns = document.querySelectorAll('button');
    return JSON.stringify(Array.from(btns).map(b => {
      const rect = b.getBoundingClientRect();
      return {
        text: b.textContent.trim().substring(0, 40),
        disabled: b.disabled,
        type: b.type,
        visible: b.offsetParent !== null,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width),
        h: Math.round(rect.height)
      };
    }));
  `);
  console.log("All buttons:", r);

  // Find and click Next button
  const btns = JSON.parse(r);
  const nextBtn = btns.find(b => b.text.includes('Next') && b.visible);
  if (nextBtn) {
    console.log("\nNext button found:", JSON.stringify(nextBtn));
    if (!nextBtn.disabled) {
      await clickAt(send, nextBtn.x, nextBtn.y);
      console.log("Clicked Next!");
      await sleep(8000);
      r = await eval_(`return window.location.href`);
      console.log("\nNew URL:", r);
      r = await eval_(`return document.body.innerText.substring(0, 5000)`);
      console.log("\nNew Page:", r);
    } else {
      console.log("Next is disabled!");
      // Re-check checkboxes
      r = await eval_(`
        const cbs = document.querySelectorAll('[role="checkbox"]');
        return JSON.stringify(Array.from(cbs).map(cb => cb.getAttribute('aria-checked')));
      `);
      console.log("Checkbox states:", r);
    }
  } else {
    console.log("No Next button found among visible buttons");
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
