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

  // Click Start
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1265827/edit" });
  await sleep(5000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 10000)`);
  console.log("\nPage:", r);

  // Get all form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea, button');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null || i.type === 'hidden' || i.type === 'radio').map(i => ({
      tag: i.tagName, type: i.type, name: i.name || '', id: i.id || '',
      value: i.value?.substring(0, 80) || '',
      text: i.textContent?.trim().substring(0, 80) || '',
      label: i.labels?.[0]?.textContent?.trim().substring(0, 80) || '',
      checked: i.checked || false
    })).slice(0, 40));
  `);
  console.log("\nForm fields:", r);

  // Check for iframes (some jobs use external forms)
  r = await eval_(`
    const iframes = document.querySelectorAll('iframe');
    return JSON.stringify(Array.from(iframes).map(f => ({
      src: f.src?.substring(0, 120),
      w: f.width, h: f.height,
      visible: f.offsetParent !== null
    })));
  `);
  console.log("\nIframes:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_lawsuit_start.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
