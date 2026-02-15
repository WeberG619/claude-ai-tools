// Fix Premium revision and save Fiverr pricing
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

  // Check if we need to fix revision 3
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 300)
    });
  `);
  console.log("Current state:", r);

  // Check for any validation errors currently showing
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const cls = el.className?.toString() || '';
        const style = window.getComputedStyle(el);
        return el.offsetParent !== null &&
               (cls.includes('error') || cls.includes('Error') || cls.includes('invalid') ||
                cls.includes('validation') || style.color === 'rgb(255, 0, 0)' || style.color === 'red') &&
               el.textContent.trim().length > 0 && el.textContent.trim().length < 100 &&
               el.children.length < 3;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 80),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(errors);
  `);
  console.log("Errors visible:", r);

  // Fix Premium revisions - click the third revision dropdown (the one showing SELECT)
  console.log("\n=== Fixing Premium Revisions ===");

  // Scroll to revisions area
  r = await eval_(`
    // Find the revision selects - they're in the same row as "Revisions" label
    // The selects have class "select-penta-design" and are inside the revisions row
    const revRow = Array.from(document.querySelectorAll('tr'))
      .find(r => {
        const first = r.querySelector('td');
        return first && first.textContent.includes('Revision');
      });
    if (!revRow) return JSON.stringify({ error: 'no rev row' });

    revRow.scrollIntoView({ block: 'center' });

    // Get all select-penta-design elements inside this row
    const selects = Array.from(revRow.querySelectorAll('.select-penta-design'));
    return JSON.stringify(selects.map((s, i) => ({
      index: i,
      text: s.textContent.trim().substring(0, 20),
      x: Math.round(s.getBoundingClientRect().x + s.getBoundingClientRect().width/2),
      y: Math.round(s.getBoundingClientRect().y + s.getBoundingClientRect().height/2),
      class: (s.className?.toString() || '').substring(0, 80)
    })));
  `);
  console.log("Rev selects:", r);
  const revSelects = JSON.parse(r);

  // Find the one that says "Select" (not yet set)
  for (const sel of revSelects) {
    if (sel.text.toLowerCase() === 'select') {
      console.log(`\nClicking unset revision: index ${sel.index} at (${sel.x}, ${sel.y})`);
      await clickAt(send, sel.x, sel.y);
      await sleep(700);

      // Find the dropdown options
      r = await eval_(`
        const items = Array.from(document.querySelectorAll('.select-penta-design-option, .table-select-option'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            text: el.textContent.trim(),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(items);
      `);
      console.log("Options:", r);
      const opts = JSON.parse(r);

      // Select "UNLIMITED" or "3"
      const target = opts.find(o => o.text === 'UNLIMITED') ||
                     opts.find(o => o.text === '3') ||
                     opts.find(o => o.text === 'Unlimited');
      if (target) {
        console.log(`Selecting: "${target.text}"`);
        await clickAt(send, target.x, target.y);
        await sleep(500);
      } else if (opts.length > 0) {
        // Just pick the 4th option (index 3 = "3" usually)
        const fallback = opts[Math.min(4, opts.length - 1)];
        console.log(`Fallback selecting: "${fallback.text}"`);
        await clickAt(send, fallback.x, fallback.y);
        await sleep(500);
      }
    }
  }

  // Also check Basic revision (first dropdown might need fixing too)
  r = await eval_(`
    const revRow = Array.from(document.querySelectorAll('tr'))
      .find(r => r.querySelector('td')?.textContent?.includes('Revision'));
    const selects = Array.from(revRow?.querySelectorAll('.select-penta-design') || []);
    return JSON.stringify(selects.map(s => s.textContent.trim().substring(0, 20)));
  `);
  console.log("\nRevision states:", r);

  // Verify all fields
  console.log("\n=== Verification ===");
  r = await eval_(`
    return JSON.stringify({
      pkg1: {
        title: document.querySelector('input[name="gig[packages][1][title]"]')?.value,
        duration: document.querySelector('input[name="gig[packages][1][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][1][price]"]')?.value,
        revActive: document.querySelector('input[name="gig[packages][1][content][614][active]"]')?.value,
        revMods: document.querySelector('input[name="gig[packages][1][content][614][pricing_factor][included_modifications]"]')?.value
      },
      pkg2: {
        title: document.querySelector('input[name="gig[packages][2][title]"]')?.value,
        duration: document.querySelector('input[name="gig[packages][2][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][2][price]"]')?.value,
        revActive: document.querySelector('input[name="gig[packages][2][content][716][active]"]')?.value,
        revMods: document.querySelector('input[name="gig[packages][2][content][716][pricing_factor][included_modifications]"]')?.value
      },
      pkg3: {
        title: document.querySelector('input[name="gig[packages][3][title]"]')?.value,
        duration: document.querySelector('input[name="gig[packages][3][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][3][price]"]')?.value,
        revActive: document.querySelector('input[name="gig[packages][3][content][818][active]"]')?.value,
        revMods: document.querySelector('input[name="gig[packages][3][content][818][pricing_factor][included_modifications]"]')?.value
      }
    });
  `);
  console.log(r);

  // Try Save & Continue
  console.log("\n=== Saving ===");
  r = await eval_(`
    const btn = document.querySelector('.btn-submit') ||
      Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
    if (btn) { btn.scrollIntoView({ block: 'center' }); btn.click(); }
    return btn ? 'clicked' : 'not found';
  `);
  console.log("Save:", r);
  await sleep(5000);

  // Check if we advanced
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="validation"], .gig-upcrate-validation-error'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100)),
      bodyStart: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("\nAfter save:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
