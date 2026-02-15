const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
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

  // Navigate to assessments page
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/assessments" });
  await sleep(4000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 6000)`);
  console.log("\nPage:", r);

  // Get all links/buttons that could be assessment actions
  r = await eval_(`
    const els = document.querySelectorAll('a, button');
    return JSON.stringify(Array.from(els).filter(e => {
      const text = e.textContent?.trim().toLowerCase() || '';
      const href = e.href || '';
      return (text.includes('start') || text.includes('take') || text.includes('begin') ||
              text.includes('assessment') || text.includes('qualify') || text.includes('uhrs') ||
              href.includes('assessment') || href.includes('qualification')) && e.offsetParent !== null;
    }).map(e => ({
      tag: e.tagName,
      text: e.textContent?.trim().substring(0, 80),
      href: e.href || '',
      class: e.className?.substring?.(0, 60) || ''
    })));
  `);
  console.log("\nAssessment links:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_assessments.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
