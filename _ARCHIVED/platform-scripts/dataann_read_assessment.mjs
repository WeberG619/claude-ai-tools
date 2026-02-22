const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("app.dataannotation");

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Get full page text in chunks
  r = await eval_(`return document.body.innerText.substring(0, 8000)`);
  console.log("\n=== PAGE PART 1 ===\n", r);

  r = await eval_(`return document.body.innerText.substring(8000, 16000)`);
  if (r && r.length > 0) console.log("\n=== PAGE PART 2 ===\n", r);

  r = await eval_(`return document.body.innerText.substring(16000, 24000)`);
  if (r && r.length > 0) console.log("\n=== PAGE PART 3 ===\n", r);

  // Get all form elements (textareas, inputs, selects, radio buttons)
  r = await eval_(`
    const elements = [];

    // Radio buttons / checkboxes
    document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => {
      const label = el.closest('label')?.textContent?.trim() || el.nextElementSibling?.textContent?.trim() || '';
      elements.push({ type: el.type, name: el.name, value: el.value, label: label.substring(0, 100), checked: el.checked });
    });

    // Textareas
    document.querySelectorAll('textarea').forEach(el => {
      const label = el.closest('div')?.querySelector('label')?.textContent?.trim() || el.placeholder || el.name || '';
      elements.push({ type: 'textarea', name: el.name, placeholder: el.placeholder?.substring(0, 50), label: label.substring(0, 100), value: el.value.substring(0, 50) });
    });

    // Select dropdowns
    document.querySelectorAll('select').forEach(el => {
      const options = Array.from(el.options).map(o => o.text.substring(0, 50));
      elements.push({ type: 'select', name: el.name, options });
    });

    return JSON.stringify(elements, null, 2);
  `);
  console.log("\n=== FORM ELEMENTS ===\n", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
