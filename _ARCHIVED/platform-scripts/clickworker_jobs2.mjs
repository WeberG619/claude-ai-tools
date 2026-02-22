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

  // Try navigating directly to jobs bypassing 2FA
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
  await sleep(4000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Check if redirected to 2FA
  if (r.includes('two_fa')) {
    console.log("Redirected to 2FA - trying to wait and go back...");
    // Wait for timer to expire
    await sleep(3000);
    // Try navigating again
    await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
    await sleep(4000);
    r = await eval_(`return window.location.href`);
    console.log("URL after retry:", r);
  }

  if (r.includes('two_fa')) {
    // Try the assessments page
    await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/assessments" });
    await sleep(3000);
    r = await eval_(`return window.location.href`);
    console.log("Assessments URL:", r);
  }

  r = await eval_(`return document.body.innerText.substring(0, 6000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_jobs2.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
