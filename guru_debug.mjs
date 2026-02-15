// Debug Guru form - find missing fields and fix skills
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) throw new Error("No Guru tab");
  const ws = new WebSocket(guru.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connect();

  // 1. Check ALL checkboxes state
  console.log("=== All checkboxes ===");
  let r = await eval_(`
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.id !== 'ProfileVisibility');
    return JSON.stringify(cbs.map(c => {
      const lbl = c.closest('label') || c.parentElement;
      return {
        text: lbl?.textContent?.trim()?.substring(0, 50) || c.id,
        checked: c.checked,
        visible: c.offsetParent !== null,
        name: c.name,
        id: c.id
      };
    }));
  `);
  console.log(r);

  // 2. Check radio buttons (Architecture type)
  console.log("\n=== Radio buttons ===");
  r = await eval_(`
    const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
    return JSON.stringify(radios.map(r => {
      const lbl = r.closest('label') || r.parentElement;
      return {
        text: lbl?.textContent?.trim()?.substring(0, 60) || r.name,
        checked: r.checked,
        name: r.name,
        id: r.id
      };
    }));
  `);
  console.log(r);

  // 3. Find ALL error/mandatory indicators with their context
  console.log("\n=== Error indicators ===");
  r = await eval_(`
    // Get all elements with "Mandatory" or "error" text/class
    const allEls = Array.from(document.querySelectorAll('*'));
    const errors = allEls.filter(el => {
      if (el.offsetParent === null && el.tagName !== 'SPAN') return false;
      const text = el.textContent?.trim() || '';
      const cls = el.className || '';
      return (text === 'Mandatory field.' || text === 'Please select at least 5 skills.' ||
              cls.includes('error') || cls.includes('mandatory'));
    }).map(el => {
      // Walk up to find context
      let ctx = el;
      for (let i = 0; i < 5; i++) {
        if (ctx.parentElement) ctx = ctx.parentElement;
      }
      return {
        text: el.textContent?.trim()?.substring(0, 100),
        tag: el.tagName,
        class: (el.className || '').substring(0, 80),
        display: window.getComputedStyle(el).display,
        parentContext: ctx.textContent?.trim()?.substring(0, 200)
      };
    });
    return JSON.stringify(errors, null, 2);
  `);
  console.log(r);

  // 4. Get the full visible form text to understand what's showing
  console.log("\n=== Full form text (scrolled sections) ===");
  r = await eval_(`
    window.scrollTo(0, 500);
    return "";
  `);
  await sleep(500);
  r = await eval_(`
    const bodyText = document.body.innerText;
    // Find the section between "Service Category" and the footer
    const catIdx = bodyText.indexOf('Service Category');
    const footerIdx = bodyText.indexOf('Navigate');
    if (catIdx > 0 && footerIdx > catIdx) {
      return bodyText.substring(catIdx, footerIdx);
    }
    return bodyText.substring(500, 2000);
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
