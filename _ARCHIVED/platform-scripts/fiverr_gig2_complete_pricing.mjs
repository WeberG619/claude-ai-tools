// Complete pricing - click delivery time and revision dropdowns at known positions
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function selectDropdownOption(send, eval_, cellX, cellY, targetText) {
  console.log(`  Clicking cell at (${cellX}, ${cellY})`);
  await clickAt(send, cellX, cellY);
  await sleep(800);

  // Check for opened dropdown - look for any new visible elements
  let r = await eval_(`
    // Look for dropdown/popup that just appeared
    const candidates = Array.from(document.querySelectorAll('[class*="option"], [class*="item"], li'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.height > 10 && rect.width > 50 &&
               Math.abs(rect.x - ${cellX}) < 200 &&
               el.textContent.trim().length > 0 && el.textContent.trim().length < 30;
      })
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        class: (el.className?.toString() || '').substring(0, 40)
      }));
    return JSON.stringify(candidates.slice(0, 20));
  `);
  console.log(`  Options found: ${r.substring(0, 200)}`);
  const options = JSON.parse(r);

  if (options.length > 0) {
    const match = options.find(o => o.text.includes(targetText)) || options[0];
    console.log(`  Selecting: "${match.text}"`);
    await clickAt(send, match.x, match.y);
    await sleep(500);
    return true;
  }
  return false;
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll to top
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // Get fresh cell positions
  let r = await eval_(`
    const rows = Array.from(document.querySelectorAll('tr'))
      .filter(el => el.offsetParent !== null)
      .map(tr => ({
        text: tr.textContent.trim().substring(0, 40).replace(/\\n/g, ' '),
        cells: Array.from(tr.querySelectorAll('td')).map(td => ({
          text: td.textContent.trim().substring(0, 20),
          x: Math.round(td.getBoundingClientRect().x + td.getBoundingClientRect().width/2),
          y: Math.round(td.getBoundingClientRect().y + td.getBoundingClientRect().height/2),
          hasDropdown: !!td.querySelector('[class*="select"], [class*="dropdown"]')
        }))
      }));
    return JSON.stringify(rows.filter(r => r.cells.some(c => c.hasDropdown)));
  `);
  console.log("Rows with dropdowns:", r);
  const dropdownRows = JSON.parse(r);

  // Process delivery time row
  const deliveryRow = dropdownRows.find(r => r.text.includes('Delivery'));
  if (deliveryRow) {
    console.log("\n=== Delivery Times ===");
    const deliveryDays = ["3 Days", "2 Days", "1 Day"];
    const dataCells = deliveryRow.cells.filter(c => c.hasDropdown);
    for (let i = 0; i < dataCells.length; i++) {
      console.log(`\nSetting delivery time ${i}:`);
      const ok = await selectDropdownOption(send, eval_, dataCells[i].x, dataCells[i].y, deliveryDays[i] || "3");
      if (!ok) {
        // Try clicking the dropdown indicator inside the cell
        r = await eval_(`
          const td = document.elementFromPoint(${dataCells[i].x}, ${dataCells[i].y});
          const inner = td?.querySelector('[class*="select"], [class*="dropdown"]') || td;
          if (inner) {
            inner.click();
            return 'clicked inner';
          }
          return 'no inner';
        `);
        console.log(`  JS click result: ${r}`);
        await sleep(800);

        // Check for options again
        r = await eval_(`
          const els = Array.from(document.querySelectorAll('*'))
            .filter(el => {
              const t = el.textContent.trim();
              return el.offsetParent !== null && el.children.length === 0 &&
                     (t.includes('Day') || t.includes('day')) && t.length < 20 &&
                     el.getBoundingClientRect().y > ${dataCells[i].y - 50};
            })
            .map(el => ({
              text: el.textContent.trim(),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }));
          return JSON.stringify(els.slice(0, 15));
        `);
        console.log(`  Day options: ${r}`);
        const dayOpts = JSON.parse(r);
        const target = dayOpts.find(o => o.text.includes(deliveryDays[i])) || dayOpts[0];
        if (target) {
          console.log(`  Clicking: "${target.text}"`);
          await clickAt(send, target.x, target.y);
          await sleep(500);
        }
      }
    }
  }

  // Process revisions row
  const revisionRow = dropdownRows.find(r => r.text.includes('Revision'));
  if (revisionRow) {
    console.log("\n=== Revisions ===");
    const dataCells = revisionRow.cells.filter(c => c.hasDropdown);
    for (let i = 0; i < dataCells.length; i++) {
      console.log(`\nSetting revision ${i}:`);
      const ok = await selectDropdownOption(send, eval_, dataCells[i].x, dataCells[i].y, "Unlimited");
      if (!ok) {
        r = await eval_(`
          const td = document.elementFromPoint(${dataCells[i].x}, ${dataCells[i].y});
          const inner = td?.querySelector('[class*="select"], [class*="dropdown"]') || td;
          if (inner) {
            inner.click();
            return 'clicked inner';
          }
          return 'no inner';
        `);
        await sleep(800);

        r = await eval_(`
          const els = Array.from(document.querySelectorAll('*'))
            .filter(el => {
              const t = el.textContent.trim();
              return el.offsetParent !== null && el.children.length === 0 &&
                     (t.includes('Unlimited') || t === '1' || t === '2' || t === '3') && t.length < 20 &&
                     el.getBoundingClientRect().y > ${dataCells[i].y - 50};
            })
            .map(el => ({
              text: el.textContent.trim(),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }));
          return JSON.stringify(els.slice(0, 15));
        `);
        console.log(`  Options: ${r}`);
        const opts = JSON.parse(r);
        const target = opts.find(o => o.text === 'Unlimited') || opts[opts.length - 1];
        if (target) {
          await clickAt(send, target.x, target.y);
          await sleep(500);
        }
      }
    }
  }

  // Verify word counts
  console.log("\n=== Verifying Word Counts ===");
  r = await eval_(`
    const wordInputs = Array.from(document.querySelectorAll('input[type="number"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 930 && el.getBoundingClientRect().y < 1000)
      .map(el => ({ value: el.value, x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
    return JSON.stringify(wordInputs);
  `);
  console.log("Words:", r);
  const wordInputs = JSON.parse(r);
  const wordCounts = ["1000", "3000", "5000"];
  for (let i = 0; i < wordInputs.length; i++) {
    if (wordInputs[i].value !== wordCounts[i]) {
      console.log(`  Fixing word count ${i}: ${wordInputs[i].value} -> ${wordCounts[i]}`);
      await clickAt(send, wordInputs[i].x, wordInputs[i].y);
      await sleep(100);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(50);
      await send("Input.insertText", { text: wordCounts[i] });
      await sleep(200);
    }
  }

  // Verify prices
  console.log("\n=== Verifying Prices ===");
  r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ value: el.value, x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
    return JSON.stringify(priceInputs);
  `);
  console.log("Prices:", r);
  const priceInputs = JSON.parse(r);
  const prices = ["10", "25", "50"];
  for (let i = 0; i < priceInputs.length; i++) {
    if (!priceInputs[i].value || priceInputs[i].value === "") {
      console.log(`  Setting price ${i} to $${prices[i]}`);
      await clickAt(send, priceInputs[i].x, priceInputs[i].y);
      await sleep(100);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(50);
      await send("Input.insertText", { text: prices[i] });
      await sleep(200);
      // Tab out to commit
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
      await sleep(200);
    }
  }

  // Check for grammar & spelling checkboxes - ensure checked for all
  console.log("\n=== Setting Checkboxes ===");
  r = await eval_(`
    const grammarRow = Array.from(document.querySelectorAll('tr'))
      .find(tr => tr.textContent.includes('Grammar & spelling'));
    if (grammarRow) {
      const cbs = Array.from(grammarRow.querySelectorAll('input[type="checkbox"]'));
      return JSON.stringify(cbs.map(cb => ({
        checked: cb.checked,
        x: Math.round(cb.getBoundingClientRect().x + cb.getBoundingClientRect().width/2),
        y: Math.round(cb.getBoundingClientRect().y + cb.getBoundingClientRect().height/2)
      })));
    }
    return '[]';
  `);
  console.log("Grammar checkboxes:", r);
  // They should already be checked

  // Final check
  await sleep(500);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\nErrors:", r);

  // Save & Continue
  console.log("\n=== Saving ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'scrolling';
    }
    return 'no button';
  `);
  await sleep(800);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 800)
      });
    `);
    const result = JSON.parse(r);
    console.log("URL after save:", result.url);
    console.log("Body:", result.body.substring(0, 400));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
