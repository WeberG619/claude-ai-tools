const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

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

  // Check for error messages
  let r = await eval_(`
    const errors = document.querySelectorAll('[class*="error"], [class*="Error"], [class*="alert"], [class*="Alert"], [class*="invalid"], [class*="Invalid"], [class*="warning"], [class*="Warning"], .field_with_errors, .help-block, .form-error');
    return JSON.stringify(Array.from(errors).filter(e => e.offsetParent !== null && e.textContent.trim().length > 0).map(e => ({
      tag: e.tagName,
      classes: (typeof e.className === 'string' ? e.className : '').substring(0, 60),
      text: e.textContent.trim().substring(0, 100)
    })));
  `);
  console.log("Errors:", r);

  // Check full page text for any error messages
  r = await eval_(`
    const text = document.body.innerText;
    const lines = text.split('\\n').filter(l => l.trim().length > 0);
    // Look for error-like lines
    return JSON.stringify(lines.filter(l =>
      l.toLowerCase().includes('error') ||
      l.toLowerCase().includes('invalid') ||
      l.toLowerCase().includes('required') ||
      l.toLowerCase().includes('already') ||
      l.toLowerCase().includes('taken') ||
      l.toLowerCase().includes('too short') ||
      l.toLowerCase().includes('must') ||
      l.toLowerCase().includes('cannot') ||
      l.toLowerCase().includes('please')
    ));
  `);
  console.log("\nError-like text:", r);

  // Take screenshot to see what Weber sees
  const screenshot = await send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false
  });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_screen.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
