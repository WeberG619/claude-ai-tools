// Fill languages & birthdate, then continue through remaining setup pages
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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
  let { ws, send, eval_ } = await connectToTab("freelancer.com");
  console.log("Connected\n");

  // Check current page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 800),
      inputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null && !i.id.includes('recaptcha'))
        .map(i => ({ tag: i.tagName, type: i.type, id: i.id, placeholder: i.placeholder, value: i.value }))
    });
  `);
  console.log("Page state:", r);

  const state = JSON.parse(r);

  if (state.url.includes("languages-and-birthdate")) {
    console.log("\n--- Languages & Birthdate ---");

    // English should already be selected. Check for language and date inputs.
    r = await eval_(`
      // Check if English is already listed
      const englishText = document.body.innerText.includes('English');

      // Find date/birthday related inputs
      const allInputs = Array.from(document.querySelectorAll('input, select'))
        .filter(i => i.offsetParent !== null && !i.id.includes('recaptcha'));

      // Check for dropdowns (month/day/year selects)
      const selects = Array.from(document.querySelectorAll('select'))
        .filter(s => s.offsetParent !== null);

      return JSON.stringify({
        hasEnglish: englishText,
        inputs: allInputs.map(i => ({ tag: i.tagName, type: i.type, id: i.id, placeholder: i.placeholder, name: i.name, options: i.tagName === 'SELECT' ? Array.from(i.options).slice(0, 5).map(o => o.text) : undefined })),
        selects: selects.map(s => ({ id: s.id, name: s.name, optCount: s.options.length, firstOpts: Array.from(s.options).slice(0, 5).map(o => ({ val: o.value, text: o.text })) }))
      });
    `);
    console.log("  Form details:", r);

    const details = JSON.parse(r);

    // If there are date selects, fill them
    // Weber's birthday from password hint: 1974 (from Weber@619.1974)
    // Let's check what inputs exist for the date
    if (details.selects.length > 0) {
      console.log("\n  Found select dropdowns, filling birth date...");
      for (const sel of details.selects) {
        console.log(`    Select: ${sel.id || sel.name}, options: ${sel.optCount}`);
      }

      // Set birthdate via Angular-aware approach
      r = await eval_(`
        const selects = Array.from(document.querySelectorAll('select'))
          .filter(s => s.offsetParent !== null);
        const results = [];
        for (const sel of selects) {
          const opts = Array.from(sel.options).map(o => o.text.toLowerCase());
          // Try to identify what this select is for
          if (opts.some(o => o.includes('january') || o.includes('jan'))) {
            // Month select - set to June (6)
            const junIdx = Array.from(sel.options).findIndex(o => o.text.toLowerCase().includes('jun'));
            if (junIdx >= 0) {
              const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
              nativeSetter.call(sel, sel.options[junIdx].value);
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              results.push('month set to June');
            }
          } else if (sel.options.length > 28 && sel.options.length <= 32) {
            // Day select
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
            nativeSetter.call(sel, '19');
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            results.push('day set to 19');
          } else if (opts.some(o => o.includes('1974') || o.includes('1990'))) {
            // Year select
            const yearIdx = Array.from(sel.options).findIndex(o => o.text.includes('1974'));
            if (yearIdx >= 0) {
              const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
              nativeSetter.call(sel, sel.options[yearIdx].value);
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              results.push('year set to 1974');
            }
          }
        }
        return JSON.stringify(results);
      `);
      console.log("  Date fill results:", r);
    }

    // Check if there's a date input (type=date or text with date format)
    r = await eval_(`
      const dateInputs = Array.from(document.querySelectorAll('input[type="date"], input[type="text"]'))
        .filter(i => i.offsetParent !== null && !i.id.includes('recaptcha'));
      return JSON.stringify(dateInputs.map(i => ({ type: i.type, id: i.id, placeholder: i.placeholder })));
    `);
    console.log("  Date inputs:", r);

    const dateInputs = JSON.parse(r);
    if (dateInputs.length > 0) {
      // Type the date
      for (const di of dateInputs) {
        if (di.placeholder?.includes('DD') || di.placeholder?.includes('date') || di.id?.includes('date') || di.id?.includes('birth')) {
          console.log("  Filling date input:", di.id || di.placeholder);
          // Focus it
          await eval_(`
            const input = document.getElementById(${JSON.stringify(di.id)}) || document.querySelector('input[placeholder="${di.placeholder}"]');
            if (input) { input.focus(); input.click(); }
          `);
          await sleep(200);

          // Triple click to select all
          const pos = await eval_(`
            const input = document.getElementById(${JSON.stringify(di.id)}) || document.querySelector('input[type="date"], input[type="text"]');
            const rect = input.getBoundingClientRect();
            return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
          `);
          const p = JSON.parse(pos);
          await send("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 3 });
          await sleep(50);
          await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 3 });
          await sleep(100);
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
          await sleep(100);
          await send("Input.insertText", { text: "06/19/1974" });
          await sleep(300);
        }
      }
    }

    // Click Next
    console.log("\n  Clicking Next...");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
      if (btn) {
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
      console.log("  Clicked Next");
    }

    await sleep(4000);
  }

  // Check what's next
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n=== Next Page ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
