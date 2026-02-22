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

  // Find and click Finish button
  let r = await eval_(`
    const btns = document.querySelectorAll('input[type="submit"], button');
    return JSON.stringify(Array.from(btns).filter(b => b.offsetParent !== null).map(b => ({
      tag: b.tagName, type: b.type, name: b.name || '',
      text: b.textContent?.trim().substring(0, 40) || '',
      value: b.value?.substring(0, 40) || ''
    })));
  `);
  console.log("Buttons:", r);

  // Click Finish/Submit
  r = await eval_(`
    let btn = document.querySelector('input[type="submit"][name="submit"]');
    if (!btn) btn = Array.from(document.querySelectorAll('input[type="submit"], button[type="submit"]')).find(b =>
      (b.value || b.textContent || '').match(/finish|submit|continue/i)
    );
    if (btn) { btn.click(); return 'clicked: ' + (btn.value || btn.textContent); }
    return 'not found';
  `);
  console.log("\nFinish:", r);
  await sleep(8000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Get interactive elements
  r = await eval_(`
    const inputs = document.querySelectorAll('input, button, a.btn, [role="button"]');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      tag: i.tagName, type: i.type || '', id: i.id || '',
      text: i.textContent?.trim().substring(0, 60) || '',
      value: i.value?.substring(0, 40) || '',
      href: i.href || ''
    })).slice(0, 20));
  `);
  console.log("\nElements:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_uhrs_nda.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
