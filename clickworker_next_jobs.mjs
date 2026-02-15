const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("clickworker") || t.url.includes("unipark")));
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

  // Cancel the LLM survey job - go back to Clickworker
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1262195/edit" });
  await sleep(4000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Cancel it
  r = await eval_(`
    const cancelBtn = document.querySelector('input[name="cancel"], #cancel_1262195, #cancel_reason_label_1262195');
    if (cancelBtn) { cancelBtn.click(); return 'clicked cancel'; }
    return 'cancel not found';
  `);
  console.log("Cancel LLM:", r);
  await sleep(3000);

  // Handle confirmation dialog if any
  r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Now go to avatar survey
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1262735/edit" });
  await sleep(4000);

  r = await eval_(`return window.location.href`);
  console.log("\nAvatar URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nAvatar page:", r);

  // Look for external survey link
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    return JSON.stringify(links.filter(a => !a.href.includes('clickworker')).map(a => ({
      text: a.textContent?.trim().substring(0, 60),
      href: a.href
    })));
  `);
  console.log("\nExternal links:", r);

  // Get form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null && i.type !== 'hidden').map(i => ({
      tag: i.tagName, type: i.type, name: i.name, id: i.id,
      value: i.value?.substring(0, 60) || '',
      label: i.labels?.[0]?.textContent?.trim().substring(0, 80) || ''
    })).slice(0, 20));
  `);
  console.log("\nForm:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
