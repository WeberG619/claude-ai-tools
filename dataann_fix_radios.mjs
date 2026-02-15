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

  // Fix Q4: Click Response A using radio name b1c5b594
  let r = await eval_(`
    const radios = document.querySelectorAll('input[type="radio"]');
    for (const radio of radios) {
      if (radio.name.startsWith('b1c5b594')) {
        const label = radio.closest('label');
        if (label && label.textContent.trim() === 'Response A') {
          radio.click();
          return 'Q4: clicked Response A (name: ' + radio.name + ')';
        }
      }
    }
    return 'Q4 Response A not found';
  `);
  console.log(r);
  await sleep(300);

  // Fix Q5: Click Response B using radio name 1aed89c0
  r = await eval_(`
    const radios = document.querySelectorAll('input[type="radio"]');
    for (const radio of radios) {
      if (radio.name.startsWith('1aed89c0')) {
        const label = radio.closest('label');
        if (label && label.textContent.includes('Response B')) {
          radio.click();
          return 'Q5: clicked Response B (label: ' + label.textContent.trim().substring(0, 40) + ')';
        }
      }
    }
    return 'Q5 Response B not found';
  `);
  console.log(r);
  await sleep(300);

  // Final verification of all checked radios/checkboxes
  r = await eval_(`
    const checked = document.querySelectorAll('input[type="radio"]:checked, input[type="checkbox"]:checked');
    const results = [];
    checked.forEach(c => {
      const label = c.closest('label')?.textContent?.trim().substring(0, 60) || '';
      results.push({ name: c.name.substring(0, 8), label });
    });
    return JSON.stringify(results, null, 2);
  `);
  console.log("\nAll checked items:\n", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
