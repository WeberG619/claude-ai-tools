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

  // Navigate to W-9 form page
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/tax_form1099/new" });
  await sleep(4000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Get form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null || i.type === 'hidden' || i.type === 'file').map(i => ({
      tag: i.tagName, type: i.type, name: i.name, id: i.id,
      value: i.value?.substring(0, 60),
      accept: i.accept || '',
      label: i.labels?.[0]?.textContent?.trim().substring(0, 80) || ''
    })).slice(0, 30));
  `);
  console.log("\nForm fields:", r);

  // Check for file upload areas
  r = await eval_(`
    const fileInputs = document.querySelectorAll('input[type="file"]');
    return JSON.stringify(Array.from(fileInputs).map(i => ({
      name: i.name, id: i.id, accept: i.accept,
      parentHTML: i.parentElement?.innerHTML?.substring(0, 200) || ''
    })));
  `);
  console.log("\nFile inputs:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
