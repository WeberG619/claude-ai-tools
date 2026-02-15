// Fix Freelancer profile using execCommand for Angular compat
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // Use execCommand approach - this fires the proper Angular input events
  const fields = [
    { id: "professional-headline", value: "Writer & Data Specialist" },
    { id: "summary", value: "Professional writer and data specialist. I deliver high-quality content and accurate data processing using AI-enhanced tools for fast, precise results across writing, research, data entry and Excel projects. Meticulous attention to detail with low error rates." },
    { id: "hourly-rate", value: "35" }
  ];

  for (const field of fields) {
    console.log(`\nField: #${field.id} -> "${field.value.substring(0, 40)}${field.value.length > 40 ? '...' : ''}" (${field.value.length} chars)`);

    // Use execCommand to properly replace the value
    let r = await eval_(`
      const el = document.getElementById(${JSON.stringify(field.id)});
      if (!el) return 'NOT FOUND';

      // Focus the element
      el.focus();

      // Select all text
      el.select ? el.select() : document.execCommand('selectAll', false, null);

      // Delete selected
      document.execCommand('delete', false, null);

      // Insert new text using execCommand (triggers Angular's input event)
      document.execCommand('insertText', false, ${JSON.stringify(field.value)});

      // Read back the value to verify (handle Angular's ngModel)
      const displayed = el.value;
      return 'set to: "' + (displayed || '').substring(0, 50) + '..." (' + (displayed || '').length + ' chars)';
    `);
    console.log("  Result:", r);
  }

  // Wait a moment for Angular to process
  await sleep(500);

  // Verify all fields
  let r = await eval_(`
    const h = document.getElementById('professional-headline');
    const s = document.getElementById('summary');
    const rate = document.getElementById('hourly-rate');
    return JSON.stringify({
      headline: h?.value,
      headlineLen: h?.value?.length,
      summary: s?.value?.substring(0, 80),
      summaryLen: s?.value?.length,
      rate: rate?.value
    });
  `);
  console.log("\nVerification:", r);

  // Now click Save
  console.log("\nSaving profile...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save' && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("Clicked Save");
  }
  await sleep(4000);

  // Check result
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [class*="validation"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 120));

    const stillNeedsProfile = document.body.innerText.includes('Complete your profile');
    const hasBidSection = document.body.innerText.includes('Place a Bid') ||
                          document.body.innerText.includes('Bid Amount') ||
                          document.body.innerText.includes('your bid');

    return JSON.stringify({
      errors: [...new Set(errors)],
      stillNeedsProfile,
      hasBidSection,
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n=== RESULT ===");
  const result = JSON.parse(r);
  console.log("Errors:", result.errors);
  console.log("Still needs profile:", result.stillNeedsProfile);
  console.log("Has bid section:", result.hasBidSection);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
