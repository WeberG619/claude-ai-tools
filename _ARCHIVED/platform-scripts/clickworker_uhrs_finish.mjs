const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab"); return; }

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

  // Enter the Microsoft email in the field
  let r = await eval_(`
    const input = document.querySelector('#output_468198161__cw_live_id, input[name*="cw_live_id"]');
    if (!input) return 'email input not found';
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeSetter.call(input, 'cw_25671709@hotmail.com');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return 'entered: ' + input.value;
  `);
  console.log("Email:", r);
  await sleep(500);

  // Click Continue
  r = await eval_(`
    const btn = document.querySelector('input[type="submit"][name="submit"]');
    if (btn) { btn.click(); return 'clicked Continue'; }
    return 'Continue not found';
  `);
  console.log("Continue:", r);
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_uhrs_done.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
