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

  // Check all links on the 2FA page — maybe there's a skip, support, or alternative
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    return JSON.stringify(links.map(a => ({
      text: a.textContent.trim().substring(0, 50),
      href: a.href?.substring(0, 80)
    })).filter(a => a.text.length > 0));
  `);
  console.log("All links:", r);

  // Try navigating to the workplace directly
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace" });
  await sleep(3000);
  r = await eval_(`return window.location.href`);
  console.log("\nWorkplace URL:", r);

  // Try jobs page
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
  await sleep(3000);
  r = await eval_(`return window.location.href`);
  console.log("Jobs URL:", r);

  // Try account settings
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/account" });
  await sleep(3000);
  r = await eval_(`return window.location.href`);
  console.log("Account URL:", r);

  // Try the user menu
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/user" });
  await sleep(3000);
  r = await eval_(`return window.location.href`);
  console.log("User URL:", r);

  r = await eval_(`return document.body.innerText.substring(0, 1000)`);
  console.log("\nPage:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
