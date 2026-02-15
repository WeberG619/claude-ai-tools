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

  // Find confirm/agree/OK button
  let r = await eval_(`
    const btns = document.querySelectorAll('input[type="submit"], button[type="submit"], a.btn');
    return JSON.stringify(Array.from(btns).filter(b => b.offsetParent !== null).map(b => ({
      tag: b.tagName, type: b.type || '', name: b.name || '',
      text: b.textContent?.trim().substring(0, 40) || '',
      value: b.value?.substring(0, 40) || '',
      href: b.href || ''
    })));
  `);
  console.log("Buttons:", r);

  // Click confirm/understand button
  r = await eval_(`
    let btn = document.querySelector('input[type="submit"][value*="confirm" i], input[type="submit"][value*="understand" i], input[type="submit"][value*="ok" i], input[type="submit"][value*="accept" i]');
    if (!btn) btn = document.querySelector('input[type="submit"]:not([name="cancel"]):not(#cancel)');
    if (btn) { btn.click(); return 'clicked: ' + (btn.value || btn.textContent); }
    return 'not found';
  `);
  console.log("\nConfirm:", r);
  await sleep(8000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_uhrs_final.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
