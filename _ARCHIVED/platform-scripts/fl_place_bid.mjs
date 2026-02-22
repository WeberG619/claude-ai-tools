// Place bid on Manual Alphanumeric Data Entry job
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
  console.log("Connected - bid form should be visible\n");

  // Verify bid form is present
  let r = await eval_(`
    const bidInput = document.getElementById('bidAmountInput');
    const periodInput = document.getElementById('periodInput');
    const descArea = document.getElementById('descriptionTextArea');
    return JSON.stringify({
      bidInputValue: bidInput?.value,
      periodValue: periodInput?.value,
      descValue: descArea?.value,
      bidInputExists: !!bidInput,
      periodExists: !!periodInput,
      descExists: !!descArea
    });
  `);
  console.log("Bid form state:", r);

  // Fill bid amount - ₹18,000 INR (below avg of ₹21,000, within ₹12,500-37,500 range)
  const bidAmount = "18000";
  console.log(`\nSetting bid amount: ₹${bidAmount} INR`);
  r = await eval_(`
    const el = document.getElementById('bidAmountInput');
    if (!el) return 'NOT FOUND';
    el.scrollIntoView({ block: 'center' });
    el.focus();
    el.select ? el.select() : document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, ${JSON.stringify(bidAmount)});
    return 'set to: ' + el.value;
  `);
  console.log("  Bid amount:", r);

  await sleep(300);

  // Fill delivery period - 5 days
  const deliveryDays = "5";
  console.log(`\nSetting delivery: ${deliveryDays} days`);
  r = await eval_(`
    const el = document.getElementById('periodInput');
    if (!el) return 'NOT FOUND';
    el.focus();
    el.select ? el.select() : document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, ${JSON.stringify(deliveryDays)});
    return 'set to: ' + el.value;
  `);
  console.log("  Days:", r);

  await sleep(300);

  // Write proposal
  const proposal = `I'm well-suited for this manual alphanumeric data entry project. I have extensive experience with precise, character-by-character data keying into Excel templates, maintaining extremely low error rates throughout.

My approach for your project:
• I will carefully key each alphanumeric value (product codes, IDs, reference strings) from your source files into the locked Excel template
• I'll follow your field notes precisely to ensure correct column placement
• No macros, OCR, or automated tools — strictly manual entry as required
• I will maintain a completion log documenting any unreadable characters or discrepancies for your review

I work methodically through large data sets, double-checking entries to ensure formatting remains untouched. I'm comfortable with repetitive, detail-oriented work and pride myself on accuracy.

Available to start immediately and deliver within 5 days. Looking forward to discussing the scope and volume of files.`;

  console.log(`\nWriting proposal (${proposal.length} chars)...`);
  r = await eval_(`
    const el = document.getElementById('descriptionTextArea');
    if (!el) return 'NOT FOUND';
    el.scrollIntoView({ block: 'center' });
    el.focus();
    el.select ? el.select() : document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, ${JSON.stringify(proposal)});
    return 'set to (' + el.value.length + ' chars): "' + el.value.substring(0, 80) + '..."';
  `);
  console.log("  Proposal:", r);

  await sleep(500);

  // Verify everything before submitting
  r = await eval_(`
    return JSON.stringify({
      bidAmount: document.getElementById('bidAmountInput')?.value,
      days: document.getElementById('periodInput')?.value,
      proposalLen: document.getElementById('descriptionTextArea')?.value?.length,
      proposalPreview: document.getElementById('descriptionTextArea')?.value?.substring(0, 100)
    });
  `);
  console.log("\n=== PRE-SUBMIT CHECK ===");
  console.log(r);

  // Check for the fee calculation display
  r = await eval_(`
    const feeText = Array.from(document.querySelectorAll('*'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('Paid to you') && el.childElementCount < 3)
      .map(el => el.textContent.trim());
    return JSON.stringify(feeText);
  `);
  console.log("Fee info:", r);

  // Click "Place Bid"
  console.log("\nClicking 'Place Bid'...");
  r = await eval_(`
    const bidBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Place Bid' && b.offsetParent !== null);
    if (bidBtn) {
      bidBtn.scrollIntoView({ block: 'center' });
      const rect = bidBtn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, disabled: bidBtn.disabled });
    }
    return null;
  `);
  console.log("Place Bid button:", r);

  if (r) {
    const pos = JSON.parse(r);
    if (!pos.disabled) {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      console.log("Clicked Place Bid!");
      await sleep(5000);
    } else {
      console.log("Button is disabled!");
    }
  }

  // Check result
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error" i], [class*="Error" i], [class*="alert" i]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 120));

    const success = document.body.innerText.includes('bid has been placed') ||
                    document.body.innerText.includes('Bid placed') ||
                    document.body.innerText.includes('successfully');

    const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="Modal" i]'))
      .filter(el => window.getComputedStyle(el).display !== 'none')
      .map(el => el.textContent?.trim()?.substring(0, 200));

    return JSON.stringify({
      url: location.href,
      errors: [...new Set(errors)],
      success,
      modals,
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n=== BID RESULT ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
