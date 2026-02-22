// Diagnose gig #3 pricing issues - check all form fields
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Full diagnostic of all inputs
  let r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null || el.type === 'hidden')
      .map((el, idx) => {
        const rect = el.getBoundingClientRect();
        const label = el.closest('tr, [class*="row"], label, li')?.textContent?.trim()?.substring(0, 40) || '';
        return {
          idx,
          tag: el.tagName,
          type: el.type || '',
          name: el.name || '',
          value: el.value?.substring(0, 50) || '',
          checked: el.checked,
          class: (el.className || '').substring(0, 50),
          placeholder: el.placeholder?.substring(0, 30) || '',
          label: label,
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          visible: rect.height > 0
        };
      });
    return JSON.stringify(allInputs);
  `);
  const inputs = JSON.parse(r);

  console.log("=== ALL INPUTS ===");
  for (const inp of inputs) {
    if (inp.type === 'hidden') continue;
    const status = inp.type === 'checkbox'
      ? (inp.checked ? '[x]' : '[ ]')
      : `val="${inp.value}"`;
    console.log(`  #${inp.idx} ${inp.tag}[${inp.type}] ${status} y=${inp.y} class="${inp.class}" label="${inp.label}"`);
  }

  // Check specifically for extras section
  console.log("\n=== EXTRAS SECTION ===");
  r = await eval_(`
    window.scrollTo(0, 2000);
    return 'scrolled';
  `);
  await sleep(500);

  r = await eval_(`
    const extraSection = document.body.innerText;
    const extraIdx = extraSection.indexOf('Add extra services');
    if (extraIdx >= 0) {
      return extraSection.substring(extraIdx, extraIdx + 800);
    }
    return 'extra section not found';
  `);
  console.log("Extras text:\n", r);

  // Check for any hidden validation errors
  r = await eval_(`
    const allErrors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [class*="warning"]'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 80),
        class: (el.className || '').substring(0, 50),
        visible: el.offsetParent !== null,
        y: Math.round(el.getBoundingClientRect().y)
      }))
      .filter(el => el.text.length > 0);
    return JSON.stringify(allErrors);
  `);
  console.log("\nAll error/invalid elements:", r);

  // Check extras checkboxes specifically
  r = await eval_(`
    const extrasArea = document.body.innerText;
    const lines = extrasArea.split('\\n').filter(l => l.trim());
    const extraStart = lines.findIndex(l => l.includes('Add extra services'));
    if (extraStart >= 0) {
      return JSON.stringify(lines.slice(extraStart, extraStart + 30));
    }
    return JSON.stringify([]);
  `);
  console.log("\nExtras lines:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
