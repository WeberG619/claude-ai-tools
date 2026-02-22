// Finish Guru profile: select work type, skills, then publish
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
  console.log("Connected\n");

  // Step 1: Select "Architecture" type of work
  console.log("Step 1: Select Architecture type...");
  let r = await eval_(`
    const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
    const labels = radios.map(r => {
      const lbl = r.closest('label') || r.parentElement;
      return { radio: r, text: lbl?.textContent?.trim() || '' };
    });
    const arch = labels.find(l => l.text === 'Architecture');
    if (arch) {
      arch.radio.click();
      return "Selected Architecture";
    }
    return "Not found. Labels: " + labels.map(l => l.text).join(', ');
  `);
  console.log("  ", r);
  await sleep(2000);

  // Step 2: Check for skill checkboxes that appeared
  console.log("\nStep 2: Check for skills...");
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null && c.id !== 'ProfileVisibility');
    if (checkboxes.length === 0) {
      // Maybe skills are displayed differently - check for any new elements
      const allLabels = Array.from(document.querySelectorAll('label'))
        .filter(l => l.offsetParent !== null)
        .map(l => l.textContent.trim())
        .filter(t => t.length > 2 && t.length < 50);
      return "No checkboxes. Labels: " + allLabels.join(', ');
    }
    return "Found " + checkboxes.length + " skill checkboxes: " + checkboxes.map(c => {
      const lbl = c.closest('label') || c.parentElement;
      return lbl?.textContent?.trim() || c.id;
    }).join(', ');
  `);
  console.log("  ", r);

  // Step 3: Take full page snapshot
  console.log("\nStep 3: Full page content...");
  r = await eval_(`
    // Get everything visible in the main content area
    const mainArea = document.querySelector('.panel') || document.querySelector('[class*="content"]') || document.body;
    const visibleText = mainArea.innerText.substring(0, 2000);
    return visibleText;
  `);
  console.log("  Page text:\n", r?.substring(0, 1000));

  // Step 4: Try clicking Publish
  console.log("\nStep 4: Click Publish...");
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    const publish = btns.find(b => b.textContent.trim() === 'Publish');
    const save = btns.find(b => b.textContent.trim() === 'Save');
    if (publish) {
      publish.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return "Found Publish button, scrolling to it";
    }
    if (save) return "Only Save found";
    return "No action buttons found";
  `);
  console.log("  ", r);
  await sleep(1000);

  // Actually click it
  r = await eval_(`
    const publish = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Publish');
    if (publish) { publish.click(); return "Publish clicked"; }
    return "not found";
  `);
  console.log("  ", r);
  await sleep(4000);

  // Step 5: Check result
  console.log("\nStep 5: Check result...");
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], .alert-danger, .validation-message, [class*="invalid"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 150));

    const success = Array.from(document.querySelectorAll('[class*="success"], .alert-success, [class*="Success"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 150));

    // Check if page changed
    return JSON.stringify({
      url: location.href,
      errors: [...new Set(errors)].slice(0, 10),
      success: success.slice(0, 5),
      pagePreview: document.body.innerText.substring(0, 500)
    }, null, 2);
  `);
  console.log("  Result:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
