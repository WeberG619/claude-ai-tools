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

  // Select the first radio option (nonprofit should have kept gate locked)
  // This is a reasonable legal position - the nonprofit had a duty of care
  let r = await eval_(`
    const radio = document.querySelector('#output_468191335__df_create_sunnamed_selection__truvf_0');
    if (radio) {
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
      radio.dispatchEvent(new Event('click', { bubbles: true }));
      return 'selected: ' + radio.value;
    }
    return 'radio not found';
  `);
  console.log("Selected:", r);
  await sleep(500);

  // Click Send
  r = await eval_(`
    const btn = document.querySelector('input[type="submit"][name="submit_job"]');
    if (btn) { btn.click(); return 'clicked Send'; }
    return 'Send not found';
  `);
  console.log("Send:", r);
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Check for next job or completion
  r = await eval_(`
    const btns = document.querySelectorAll('input[type="submit"], button, a.btn, a[href*="edit"]');
    return JSON.stringify(Array.from(btns).filter(b => b.offsetParent !== null).map(b => ({
      tag: b.tagName, type: b.type || '', name: b.name || '',
      text: b.textContent?.trim().substring(0, 60) || '',
      value: b.value?.substring(0, 40) || '',
      href: b.href || ''
    })).slice(0, 15));
  `);
  console.log("\nButtons:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
