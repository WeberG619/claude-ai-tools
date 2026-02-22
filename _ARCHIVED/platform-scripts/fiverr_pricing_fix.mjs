// Fix Fiverr pricing - set delivery times, fix revisions, then save
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

  // === Fix Delivery Times ===
  console.log("=== Setting Delivery Times ===");
  // The delivery time dropdowns have class "pkg-duration-input"
  // There are 3 of them (Basic, Standard, Premium)
  const deliveryDays = ["1 Day", "2 Days", "3 Days"];

  for (let i = 0; i < 3; i++) {
    console.log(`\n--- Delivery Time ${i}: ${deliveryDays[i]} ---`);

    // Get the dropdown's coordinates
    let r = await eval_(`
      const dropdowns = document.querySelectorAll('.pkg-duration-input');
      const dd = dropdowns[${i}];
      if (!dd) return JSON.stringify({ error: 'not found' });
      dd.scrollIntoView({ block: 'center' });
      const rect = dd.getBoundingClientRect();
      return JSON.stringify({
        text: dd.textContent.trim().substring(0, 30),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width)
      });
    `);
    console.log("Dropdown:", r);
    const dd = JSON.parse(r);
    if (dd.error) continue;

    // Click to open
    await clickAt(send, dd.x, dd.y);
    await sleep(500);

    // Find the dropdown options (they should appear as a popover/list)
    r = await eval_(`
      // Look for dropdown option list that just appeared
      const options = Array.from(document.querySelectorAll('.select-penta-design-option, [class*="select-option"], [class*="option-item"], [class*="dropdown-item"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          h: Math.round(el.getBoundingClientRect().height),
          class: (el.className?.toString() || '').substring(0, 60)
        }));

      // Also check for ul/li options in a dropdown
      const listItems = Array.from(document.querySelectorAll('ul.select-penta-design-options li, [class*="select-penta"] li, [class*="options-list"] li'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          class: (el.className?.toString() || '').substring(0, 60)
        }));

      return JSON.stringify({ options, listItems });
    `);
    console.log("Options found:", r);
    const optData = JSON.parse(r);
    const allOpts = [...optData.options, ...optData.listItems];

    if (allOpts.length === 0) {
      // Try broader search - look for any newly visible list/popup
      r = await eval_(`
        const popups = Array.from(document.querySelectorAll('ul, [class*="popup"], [class*="popover"], [class*="menu"]'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return el.offsetParent !== null && rect.height > 50 && rect.height < 500;
          })
          .map(el => ({
            tag: el.tagName,
            class: (el.className?.toString() || '').substring(0, 80),
            childCount: el.children.length,
            html: el.innerHTML?.substring(0, 500),
            y: Math.round(el.getBoundingClientRect().y)
          }));
        return JSON.stringify(popups.slice(0, 5));
      `);
      console.log("Popup search:", r);

      // Try getting all li elements near the dropdown
      r = await eval_(`
        const items = Array.from(document.querySelectorAll('li'))
          .filter(el => {
            if (!el.offsetParent) return false;
            const rect = el.getBoundingClientRect();
            const t = el.textContent.trim().toLowerCase();
            return rect.height > 20 && rect.height < 60 &&
                   (t.includes('day') || t.includes('hour') || /^\\d+$/.test(t));
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(items);
      `);
      console.log("Day/hour items:", r);
      const dayItems = JSON.parse(r);

      if (dayItems.length > 0) {
        const targetDay = i + 1;
        const match = dayItems.find(d => d.text.includes(`${targetDay} Day`) || d.text.includes(`${targetDay} day`)) ||
                      dayItems.find(d => d.text === `${targetDay}`) ||
                      dayItems[Math.min(i, dayItems.length - 1)];
        if (match) {
          console.log(`Clicking: "${match.text}" at (${match.x}, ${match.y})`);
          await clickAt(send, match.x, match.y);
          await sleep(300);
        }
      }
    } else {
      const targetDay = i + 1;
      const match = allOpts.find(o => o.text.includes(`${targetDay} Day`) || o.text.includes(`${targetDay} day`)) ||
                    allOpts.find(o => o.text === `${targetDay}`) ||
                    allOpts[Math.min(i, allOpts.length - 1)];
      if (match) {
        console.log(`Clicking: "${match.text}" at (${match.x}, ${match.y})`);
        await clickAt(send, match.x, match.y);
        await sleep(300);
      }
    }

    // Verify
    r = await eval_(`
      return document.querySelector('input[name="gig[packages][${i+1}][duration]"]')?.value || 'not set';
    `);
    console.log(`Duration hidden field: ${r}`);
  }

  // === Fix Premium Revisions (package 3) ===
  console.log("\n\n=== Fixing Premium Revisions ===");
  // Revisions are in a row with custom selects. The table cells after the label are the 3 package dropdowns.
  let r = await eval_(`
    // Find all revision-related selects
    const revRow = Array.from(document.querySelectorAll('tr'))
      .find(r => {
        const firstCell = r.querySelector('td, th');
        return firstCell && firstCell.textContent.includes('Revisions');
      });
    if (!revRow) return JSON.stringify({ error: 'revision row not found' });

    revRow.scrollIntoView({ block: 'center' });
    const cells = Array.from(revRow.querySelectorAll('td'));
    // Skip first cell (label), get dropdowns in cells 1, 2, 3
    const dropdowns = cells.slice(1).map((cell, i) => {
      const select = cell.querySelector('.select-penta-design, [class*="select"]');
      if (!select) return { cellIndex: i+1, error: 'no select found' };
      const rect = select.getBoundingClientRect();
      return {
        cellIndex: i+1,
        text: select.textContent.trim().substring(0, 20),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width)
      };
    });
    return JSON.stringify(dropdowns);
  `);
  console.log("Revision dropdowns:", r);
  const revDropdowns = JSON.parse(r);

  // Check which ones still need to be set
  for (let i = 0; i < revDropdowns.length; i++) {
    const dd = revDropdowns[i];
    if (dd.error || dd.text === 'SELECT' || dd.text === 'Select') {
      const targetRev = i === 0 ? 1 : (i === 1 ? 2 : 3);
      console.log(`\nSetting revision for package ${i+1}: ${targetRev === 3 ? 'Unlimited' : targetRev}`);

      // Re-get coordinates after scroll
      const coords = await eval_(`
        const revRow = Array.from(document.querySelectorAll('tr'))
          .find(r => r.querySelector('td, th')?.textContent?.includes('Revisions'));
        const cells = Array.from(revRow.querySelectorAll('td'));
        const select = cells[${i+1}]?.querySelector('.select-penta-design, [class*="select"]');
        if (!select) return JSON.stringify({ error: 'not found' });
        const rect = select.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      `);
      const c = JSON.parse(coords);

      await clickAt(send, c.x, c.y);
      await sleep(500);

      // Find the options
      r = await eval_(`
        const items = Array.from(document.querySelectorAll('li'))
          .filter(el => {
            if (!el.offsetParent) return false;
            const rect = el.getBoundingClientRect();
            const t = el.textContent.trim();
            return rect.height > 15 && rect.height < 60 &&
                   (/^\\d+$/.test(t) || t === 'UNLIMITED' || t === 'Select');
          })
          .map(el => ({
            text: el.textContent.trim(),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(items);
      `);
      const opts = JSON.parse(r);
      console.log(`Options: ${opts.map(o => o.text).join(', ')}`);

      if (opts.length > 0) {
        let match;
        if (targetRev === 3) {
          match = opts.find(o => o.text === 'UNLIMITED') || opts.find(o => o.text === '3');
        } else {
          match = opts.find(o => o.text === `${targetRev}`);
        }
        match = match || opts[Math.min(targetRev, opts.length - 1)];
        if (match) {
          console.log(`Selecting: "${match.text}"`);
          await clickAt(send, match.x, match.y);
          await sleep(300);
        }
      }
    } else {
      console.log(`Package ${i+1} revision already set: "${dd.text}"`);
    }
  }

  // === Verify all fields ===
  console.log("\n\n=== Full Verification ===");
  r = await eval_(`
    return JSON.stringify({
      pkg1: {
        title: document.querySelector('input[name="gig[packages][1][title]"]')?.value,
        desc: (document.querySelector('input[name="gig[packages][1][description]"]')?.value || '').substring(0, 40),
        duration: document.querySelector('input[name="gig[packages][1][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][1][price]"]')?.value
      },
      pkg2: {
        title: document.querySelector('input[name="gig[packages][2][title]"]')?.value,
        desc: (document.querySelector('input[name="gig[packages][2][description]"]')?.value || '').substring(0, 40),
        duration: document.querySelector('input[name="gig[packages][2][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][2][price]"]')?.value
      },
      pkg3: {
        title: document.querySelector('input[name="gig[packages][3][title]"]')?.value,
        desc: (document.querySelector('input[name="gig[packages][3][description]"]')?.value || '').substring(0, 40),
        duration: document.querySelector('input[name="gig[packages][3][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][3][price]"]')?.value
      },
      revisions: {
        pkg1: document.querySelector('input[name="gig[packages][1][content][614][pricing_factor][included_modifications]"]')?.value,
        pkg2: document.querySelector('input[name="gig[packages][2][content][716][pricing_factor][included_modifications]"]')?.value,
        pkg3: document.querySelector('input[name="gig[packages][3][content][818][pricing_factor][included_modifications]"]')?.value
      }
    });
  `);
  console.log(r);

  const state = JSON.parse(r);
  const allSet = state.pkg1.duration !== "0" && state.pkg2.duration !== "0" && state.pkg3.duration !== "0" &&
                 state.pkg1.price && state.pkg2.price && state.pkg3.price;

  if (!allSet) {
    console.log("\nWARNING: Some fields still not set. Not saving yet.");
    console.log("Missing durations:", state.pkg1.duration, state.pkg2.duration, state.pkg3.duration);
  } else {
    // Click Save & Continue
    console.log("\n=== Saving ===");
    r = await eval_(`
      const btn = document.querySelector('.btn-submit') ||
        Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
      if (btn) { btn.scrollIntoView({ block: 'center' }); btn.click(); }
      return btn ? 'clicked' : 'not found';
    `);
    console.log("Save button:", r);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="validation"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
          .map(el => el.textContent.trim().substring(0, 80)),
        bodyStart: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("\nAfter save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
