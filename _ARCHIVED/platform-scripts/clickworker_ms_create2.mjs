const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("live.com") || t.url.includes("microsoft")));
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

  // Find the "Create an account" element - could be any tag
  let r = await eval_(`
    const allEls = document.querySelectorAll('*');
    const found = [];
    for (const el of allEls) {
      if (el.textContent?.includes('Create') && el.children.length === 0) {
        found.push({
          tag: el.tagName, id: el.id, class: el.className?.substring?.(0, 60) || '',
          text: el.textContent.trim().substring(0, 60),
          href: el.href || '',
          onclick: el.onclick ? 'has onclick' : '',
          role: el.getAttribute('role') || '',
          tabindex: el.getAttribute('tabindex') || ''
        });
      }
    }
    return JSON.stringify(found);
  `);
  console.log("Create elements:", r);

  // Also search for #signup or similar IDs
  r = await eval_(`
    const signup = document.querySelector('#signup, #createAccount, [data-testid="signup"], a[id*="signup"], a[id*="create"]');
    if (signup) return JSON.stringify({tag: signup.tagName, id: signup.id, class: signup.className, href: signup.href || '', text: signup.textContent.trim().substring(0, 60)});
    return 'not found';
  `);
  console.log("\nSignup element:", r);

  // Get the full HTML around "Create an account"
  r = await eval_(`
    const body = document.body.innerHTML;
    const idx = body.indexOf('Create an account');
    if (idx === -1) return 'not found in HTML';
    return body.substring(Math.max(0, idx - 300), idx + 200);
  `);
  console.log("\nHTML context:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
