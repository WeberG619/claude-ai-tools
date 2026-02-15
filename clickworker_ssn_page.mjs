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

  // Navigate to SSN/tax details page
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/tax_details/new" });
  await sleep(4000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Get ALL form fields including hidden/checkboxes
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea');
    return JSON.stringify(Array.from(inputs).map(i => ({
      tag: i.tagName, type: i.type, name: i.name, id: i.id,
      value: i.value?.substring(0, 60),
      checked: i.checked || false,
      visible: i.offsetParent !== null || i.offsetWidth > 0,
      label: i.labels?.[0]?.textContent?.trim().substring(0, 80) || '',
      placeholder: i.placeholder?.substring(0, 40) || ''
    })).slice(0, 40));
  `);
  console.log("\nAll form fields:", r);

  // Check for corporate/EIN switch
  r = await eval_(`
    const el = document.querySelector('#isCorporateSwitch');
    if (el) return 'found: checked=' + el.checked + ' type=' + el.type;
    return 'not found';
  `);
  console.log("\nCorporate switch:", r);

  // Get full page HTML to understand structure
  r = await eval_(`
    const form = document.querySelector('form');
    return form ? form.innerHTML.substring(0, 3000) : 'no form found';
  `);
  console.log("\nForm HTML:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
