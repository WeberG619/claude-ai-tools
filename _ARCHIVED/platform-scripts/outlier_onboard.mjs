const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  await sleep(3000); // Wait for page to fully load

  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
  if (!tab) { console.log("No Outlier tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r));
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

  // Bring to front
  await send("Page.bringToFront");

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  r = await eval_(`return document.body.innerText.substring(0, 6000)`);
  console.log("\nPage content:");
  console.log(r);

  // Check for form elements
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, type: el.type, name: el.name,
        placeholder: el.placeholder, id: el.id, value: el.value
      }));
    const btns = Array.from(document.querySelectorAll('a, button, [role="button"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60)
      .map(el => ({
        text: el.textContent.trim(),
        href: el.href || '',
        tag: el.tagName
      }));
    return JSON.stringify({ inputs, buttons: btns }, null, 2);
  `);
  console.log("\nForm elements:");
  console.log(r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
