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

  // Click Continue button
  await clickAt(send, 1936, 887);
  console.log("Clicked Continue");
  await sleep(8000);

  let r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Check for errors
  r = await eval_(`
    const errors = document.querySelectorAll('[class*="error"], [class*="Error"], [class*="alert"], [class*="Alert"], .field_with_errors, .help-block');
    return JSON.stringify(Array.from(errors).filter(e => e.offsetParent !== null && e.textContent.trim().length > 0).map(e => e.textContent.trim().substring(0, 100)));
  `);
  console.log("\nErrors:", r);

  // Check for form fields (to see if we moved to step 2)
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      type: i.type, name: i.name, placeholder: i.placeholder?.substring(0, 30)
    })));
  `);
  console.log("\nInputs:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
