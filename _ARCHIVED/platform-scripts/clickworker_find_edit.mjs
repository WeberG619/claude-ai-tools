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

  // Navigate to contact details
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/contact_details" });
  await sleep(4000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Find all clickable elements (links, buttons) on the page
  r = await eval_(`
    const els = document.querySelectorAll('a, button, [role="button"], input[type="button"], input[type="submit"]');
    return JSON.stringify(Array.from(els).filter(e => e.offsetParent !== null || e.offsetWidth > 0).map(e => ({
      tag: e.tagName,
      text: e.textContent?.trim().substring(0, 80),
      href: e.href || '',
      class: e.className?.substring?.(0, 80) || '',
      id: e.id || ''
    })));
  `);
  console.log("\nClickable elements:", r);

  // Also check for any edit-related links/icons
  r = await eval_(`
    const all = document.querySelectorAll('a[href*="edit"], a[href*="change"], a[href*="update"], .edit, .fa-edit, .fa-pencil, [data-action*="edit"]');
    return JSON.stringify(Array.from(all).map(e => ({
      tag: e.tagName,
      text: e.textContent?.trim().substring(0, 80),
      href: e.href || '',
      class: e.className?.substring?.(0, 80) || ''
    })));
  `);
  console.log("\nEdit-related elements:", r);

  // Check full page HTML structure around the contact info
  r = await eval_(`
    const main = document.querySelector('main, .main-content, .content, [role="main"]');
    return (main || document.body).innerHTML.substring(0, 5000);
  `);
  console.log("\nPage HTML:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
