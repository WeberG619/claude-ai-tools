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

  // Navigate to Pick a Side in This Lawsuit #2
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs/1265831/edit" });
  await sleep(5000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Check if we need to agree to something first
  if (r.includes('confirm_agreement') || r.includes('confirm_instruction')) {
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nAgreement page:", r);
    // Click Agree
    r = await eval_(`
      const btn = document.querySelector('input[type="submit"][value="Agree"], input[type="submit"][name="confirm"]');
      if (btn) { btn.click(); return 'clicked Agree'; }
      return 'no agree button';
    `);
    console.log("Agree:", r);
    await sleep(3000);
    r = await eval_(`return window.location.href`);
    console.log("URL after agree:", r);
  }

  // Check if we need to confirm instructions
  if (r.includes('confirm_instruction')) {
    r = await eval_(`
      const btn = document.querySelector('input[type="submit"][value="Agree"], input[type="submit"][name="confirm"]');
      if (btn) { btn.click(); return 'clicked confirm'; }
      return 'no confirm button';
    `);
    console.log("Confirm:", r);
    await sleep(3000);
    r = await eval_(`return window.location.href`);
    console.log("URL after confirm:", r);
  }

  r = await eval_(`return document.body.innerText.substring(0, 8000)`);
  console.log("\nPage:", r);

  // Get form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"], textarea, select');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null || i.type === 'radio').map(i => ({
      tag: i.tagName, type: i.type, name: i.name || '', id: i.id || '',
      value: i.value?.substring(0, 100) || '',
      label: i.labels?.[0]?.textContent?.trim().substring(0, 100) || '',
      checked: i.checked || false
    })).slice(0, 20));
  `);
  console.log("\nForm:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
