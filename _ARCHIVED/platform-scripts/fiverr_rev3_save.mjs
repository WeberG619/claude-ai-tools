// Fix Premium revision select and save Fiverr pricing
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Step 1: Click Premium revision dropdown and select "3"
  console.log("=== Setting Premium Revision ===");

  // Scroll revisions row into center of viewport
  let r = await eval_(`
    const revRow = Array.from(document.querySelectorAll('tr'))
      .find(r => r.querySelector('td')?.textContent?.includes('Revision'));
    if (revRow) revRow.scrollIntoView({ block: 'center' });
    // Get the 3rd select-penta-design inside the revisions row
    const selects = Array.from(revRow?.querySelectorAll('.select-penta-design') || []);
    const target = selects[2]; // Premium (3rd)
    if (!target) return JSON.stringify({ error: 'no 3rd revision select' });
    const rect = target.getBoundingClientRect();
    return JSON.stringify({
      text: target.textContent.trim(),
      x: Math.round(rect.x + rect.width/2),
      y: Math.round(rect.y + rect.height/2)
    });
  `);
  console.log("Premium rev select:", r);
  const revSelect = JSON.parse(r);

  if (revSelect.text === 'Select' || revSelect.text.toLowerCase() === 'select') {
    // Click to open dropdown
    await clickAt(send, revSelect.x, revSelect.y);
    await sleep(700);

    // Get options - look for the specific class used by this dropdown
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('.table-select-option, .select-penta-design-option'))
        .filter(el => el.offsetParent !== null)
        .map(el => {
          const rect = el.getBoundingClientRect();
          return {
            text: el.textContent.trim(),
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2),
            inViewport: rect.y > 0 && rect.y < window.innerHeight
          };
        });
      return JSON.stringify(opts);
    `);
    console.log("Options:", r);
    const opts = JSON.parse(r);

    // Select "3" (it should be in viewport)
    const target = opts.find(o => o.text === '3' && o.inViewport) ||
                   opts.find(o => o.text === '3');
    if (target) {
      if (!target.inViewport) {
        // Scroll the option into view
        await eval_(`
          const opt = Array.from(document.querySelectorAll('.table-select-option'))
            .find(el => el.textContent.trim() === '3');
          if (opt) opt.scrollIntoView({ block: 'center' });
        `);
        await sleep(200);
        // Re-get coordinates
        const newR = await eval_(`
          const opt = Array.from(document.querySelectorAll('.table-select-option'))
            .find(el => el.textContent.trim() === '3' && el.offsetParent !== null);
          if (!opt) return JSON.stringify({ error: 'not found' });
          const rect = opt.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        `);
        const newCoords = JSON.parse(newR);
        console.log(`Clicking "3" at (${newCoords.x}, ${newCoords.y})`);
        await clickAt(send, newCoords.x, newCoords.y);
      } else {
        console.log(`Clicking "3" at (${target.x}, ${target.y})`);
        await clickAt(send, target.x, target.y);
      }
      await sleep(500);
    }
  }

  // Verify revision was set
  r = await eval_(`
    const revRow = Array.from(document.querySelectorAll('tr'))
      .find(r => r.querySelector('td')?.textContent?.includes('Revision'));
    const selects = Array.from(revRow?.querySelectorAll('.select-penta-design') || []);
    return JSON.stringify(selects.map(s => s.textContent.trim()));
  `);
  console.log("Revision states after fix:", r);

  // Also check the hidden fields
  r = await eval_(`
    return JSON.stringify({
      pkg3_revActive: document.querySelector('input[name="gig[packages][3][content][818][active]"]')?.value,
      pkg3_revMods: document.querySelector('input[name="gig[packages][3][content][818][pricing_factor][included_modifications]"]')?.value,
      allDurations: [1,2,3].map(i => document.querySelector('input[name="gig[packages]['+i+'][duration]"]')?.value),
      allPrices: [1,2,3].map(i => document.querySelector('input[name="gig[packages]['+i+'][price]"]')?.value)
    });
  `);
  console.log("Hidden fields:", r);

  // Step 2: Try saving
  console.log("\n=== Attempting Save ===");

  // First try clicking the Save button and watch for errors
  r = await eval_(`
    const btn = document.querySelector('.btn-submit');
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      return JSON.stringify({
        text: btn.textContent.trim(),
        disabled: btn.disabled,
        class: (btn.className?.toString() || '').substring(0, 80)
      });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Save button info:", r);

  // Click save
  await eval_(`document.querySelector('.btn-submit')?.click()`);
  await sleep(3000);

  // Check for any errors
  r = await eval_(`
    const allText = document.body?.innerText || '';
    // Look for common error patterns
    const errorPatterns = ['Please', 'required', 'invalid', 'error', 'minimum', 'select'];
    const errorEls = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        if (!el.offsetParent) return false;
        const cls = el.className?.toString() || '';
        const style = window.getComputedStyle(el);
        const isError = cls.includes('error') || cls.includes('Error') ||
                       cls.includes('invalid') || cls.includes('validation') ||
                       cls.includes('warning') || cls.includes('alert') ||
                       style.color === 'rgb(255, 0, 0)';
        return isError && el.textContent.trim().length > 0 && el.textContent.trim().length < 200 && el.children.length < 5;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 100),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y),
        color: window.getComputedStyle(el).color
      }));

    return JSON.stringify({ errors: errorEls, url: location.href });
  `);
  console.log("Error check:", r);

  // Wait more and check again
  await sleep(3000);
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim() || '',
      bodyStart: document.body?.innerText?.substring(0, 300)
    });
  `);
  console.log("Final state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
