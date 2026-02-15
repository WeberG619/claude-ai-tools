// Fill ZIP code and additional address fields, then save
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

  // Check all visible inputs to find the ZIP/City/State fields
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(i => i.offsetParent !== null && i.type !== 'hidden')
      .map(i => ({
        tag: i.tagName, type: i.type, id: i.id, name: i.name,
        placeholder: i.placeholder?.substring(0, 50),
        value: i.value?.substring(0, 50),
        label: i.labels?.[0]?.textContent?.trim()?.substring(0, 40) || '',
        parentText: i.parentElement?.textContent?.trim()?.substring(0, 60) || ''
      }));
    return JSON.stringify(inputs);
  `);
  console.log("All inputs:", r);

  const inputs = JSON.parse(r);

  // Find and fill ZIP code field
  const zipInput = inputs.find(i =>
    i.label.toLowerCase().includes('zip') ||
    i.label.toLowerCase().includes('postal') ||
    i.placeholder?.toLowerCase()?.includes('zip') ||
    i.placeholder?.toLowerCase()?.includes('postal') ||
    i.parentText?.toLowerCase()?.includes('zip')
  );
  console.log("\nZIP input:", JSON.stringify(zipInput));

  // Find city and state inputs too
  const cityInput = inputs.find(i => i.label.toLowerCase().includes('city'));
  const stateInput = inputs.find(i => i.label.toLowerCase().includes('state') || i.label.toLowerCase().includes('province'));

  console.log("City input:", JSON.stringify(cityInput));
  console.log("State input:", JSON.stringify(stateInput));

  // Fill ZIP code
  if (zipInput) {
    console.log("\nFilling ZIP code...");
    // Use a generic selector approach - find by label text
    r = await eval_(`
      const labels = Array.from(document.querySelectorAll('label'));
      const zipLabel = labels.find(l => l.textContent.trim().toLowerCase().includes('zip') || l.textContent.trim().toLowerCase().includes('postal'));
      if (zipLabel) {
        const input = zipLabel.parentElement?.querySelector('input') || document.getElementById(zipLabel.htmlFor);
        if (input) {
          input.focus();
          input.select ? input.select() : document.execCommand('selectAll', false, null);
          document.execCommand('delete', false, null);
          document.execCommand('insertText', false, '98101');
          return 'set to: ' + input.value;
        }
      }
      // Fallback: find input after the address that's empty
      const allInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'))
        .filter(i => i.offsetParent !== null && !i.value && !i.id);
      for (const inp of allInputs) {
        const parent = inp.closest('div')?.textContent || '';
        if (parent.toLowerCase().includes('zip') || parent.toLowerCase().includes('postal')) {
          inp.focus();
          document.execCommand('insertText', false, '98101');
          return 'fallback set to: ' + inp.value;
        }
      }
      return 'NOT FOUND';
    `);
    console.log("  Result:", r);
  }

  // Fill city if empty
  if (cityInput && !cityInput.value) {
    console.log("\nFilling city...");
    r = await eval_(`
      const labels = Array.from(document.querySelectorAll('label'));
      const cityLabel = labels.find(l => l.textContent.trim() === 'City');
      if (cityLabel) {
        const input = cityLabel.parentElement?.querySelector('input') || document.getElementById(cityLabel.htmlFor);
        if (input) {
          input.focus();
          document.execCommand('insertText', false, 'Seattle');
          return 'set to: ' + input.value;
        }
      }
      return 'NOT FOUND';
    `);
    console.log("  Result:", r);
  }

  // Fill state if empty
  if (stateInput && !stateInput.value) {
    console.log("\nFilling state...");
    r = await eval_(`
      const labels = Array.from(document.querySelectorAll('label'));
      const stateLabel = labels.find(l => l.textContent.trim().includes('State'));
      if (stateLabel) {
        const input = stateLabel.parentElement?.querySelector('input') || document.getElementById(stateLabel.htmlFor);
        if (input) {
          input.focus();
          document.execCommand('insertText', false, 'Washington');
          return 'set to: ' + input.value;
        }
      }
      return 'NOT FOUND';
    `);
    console.log("  Result:", r);
  }

  await sleep(500);

  // Verify all fields
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea'))
      .filter(i => i.offsetParent !== null && i.type !== 'hidden')
      .map(i => ({
        id: i.id || 'none',
        label: i.labels?.[0]?.textContent?.trim()?.substring(0, 30) || '',
        value: i.value?.substring(0, 50) || '',
        tag: i.tagName
      }));
    return JSON.stringify(inputs);
  `);
  console.log("\n=== PRE-SAVE CHECK ===");
  console.log(r);

  // Click Save
  console.log("\nClicking Save...");
  r = await eval_(`
    const saveBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save' && b.offsetParent !== null);
    if (saveBtn) {
      saveBtn.scrollIntoView({ block: 'center' });
      const rect = saveBtn.getBoundingClientRect();
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
    await sleep(5000);
  }

  // Check result
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error" i], [class*="Error" i], [class*="validation" i]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 120));

    const completeProfile = document.body.innerText.includes('Complete your profile');
    const placeBid = document.body.innerText.includes('Place a Bid') || document.body.innerText.includes('Place Bid');
    const bidAmount = document.body.innerText.includes('Bid Amount') || document.body.innerText.includes('Your bid');

    // Check for bid form elements
    const bidInputs = Array.from(document.querySelectorAll('input, textarea'))
      .filter(i => i.offsetParent !== null && i.type !== 'hidden')
      .map(i => ({
        id: i.id || 'none',
        placeholder: i.placeholder?.substring(0, 50) || '',
        tag: i.tagName
      }));

    return JSON.stringify({
      errors: [...new Set(errors)],
      completeProfile,
      placeBid,
      bidAmount,
      bidInputs,
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => b.textContent.trim().substring(0, 40)),
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n=== AFTER SAVE ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
