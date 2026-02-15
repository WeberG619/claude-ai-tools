// Fix revisions - scroll dropdown into view or use JS click
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

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll down so the revision row is at top of viewport
  await eval_(`window.scrollTo(0, 600)`);
  await sleep(500);

  // Get revision dropdowns
  let r = await eval_(`
    const drops = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y > 0 && rect.y < 1000 &&
               !el.className.includes('duration');
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        class: (el.className?.toString() || '').substring(0, 60)
      }));
    return JSON.stringify(drops);
  `);
  console.log("Visible table-select dropdowns:", r);
  const drops = JSON.parse(r);
  const revDrops = drops.filter(d => d.text === 'Select' || d.text === 'UNLIMITED');

  for (let i = 0; i < revDrops.length; i++) {
    if (revDrops[i].text === 'UNLIMITED') {
      console.log(`Revision ${i} already set to UNLIMITED`);
      continue;
    }

    console.log(`\nSetting revision ${i} - clicking at (${revDrops[i].x}, ${revDrops[i].y})`);
    await clickAt(send, revDrops[i].x, revDrops[i].y);
    await sleep(1000);

    // Find and click UNLIMITED using JS (scroll into view first)
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('.table-select-option'))
        .filter(el => el.textContent.trim() === 'UNLIMITED' && el.offsetParent !== null);
      if (options.length > 0) {
        // Scroll the option into view
        const opt = options[0];
        opt.scrollIntoView({ block: 'center' });
        const rect = opt.getBoundingClientRect();
        return JSON.stringify({
          text: opt.textContent.trim(),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          visible: rect.y > 0 && rect.y < window.innerHeight
        });
      }
      return JSON.stringify({ error: 'no UNLIMITED option' });
    `);
    console.log(`  UNLIMITED option: ${r}`);
    const unlimitedOpt = JSON.parse(r);

    if (!unlimitedOpt.error && unlimitedOpt.visible) {
      console.log(`  Clicking UNLIMITED at (${unlimitedOpt.x}, ${unlimitedOpt.y})`);
      await clickAt(send, unlimitedOpt.x, unlimitedOpt.y);
      await sleep(500);
    } else if (!unlimitedOpt.error) {
      // Use JS click as fallback
      console.log("  Using JS click on UNLIMITED");
      r = await eval_(`
        const options = Array.from(document.querySelectorAll('.table-select-option'))
          .filter(el => el.textContent.trim() === 'UNLIMITED' && el.offsetParent !== null);
        if (options.length > 0) {
          options[0].click();
          return 'clicked';
        }
        return 'not found';
      `);
      console.log(`  JS click: ${r}`);
      await sleep(500);
    }
  }

  // Verify
  await sleep(500);
  r = await eval_(`
    const revs = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && !el.className.includes('duration') && rect.y > 0;
      })
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(revs);
  `);
  console.log("\nRevisions after fix:", r);

  // If revisions still not set, try a completely different approach
  const revValues = JSON.parse(r);
  if (revValues.some(v => v === 'Select')) {
    console.log("\nStill not set. Trying mouseDown directly on UNLIMITED buttons...");

    for (let i = 0; i < 3; i++) {
      // Open the dropdown
      const revDrop = revDrops[i];
      if (!revDrop || revDrop.text === 'UNLIMITED') continue;

      console.log(`\nRetry revision ${i}`);
      await clickAt(send, revDrop.x, revDrop.y);
      await sleep(1000);

      // Get fresh UNLIMITED position after scrollIntoView
      r = await eval_(`
        const unlimitedBtns = Array.from(document.querySelectorAll('button.table-select-option, .table-select-option'))
          .filter(el => el.textContent.trim() === 'UNLIMITED' && el.offsetParent !== null);
        if (unlimitedBtns.length > 0) {
          const btn = unlimitedBtns[0];
          btn.scrollIntoView({ block: 'nearest' });
          return new Promise(r => setTimeout(() => {
            const rect = btn.getBoundingClientRect();
            r(JSON.stringify({
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2),
              inView: rect.y > 0 && rect.y < window.innerHeight
            }));
          }, 300));
        }
        return JSON.stringify({ error: 'none' });
      `);
      console.log(`  UNLIMITED pos: ${r}`);
      const pos = JSON.parse(r);

      if (pos.inView) {
        // Use mouseMove first, then click
        await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: pos.x, y: pos.y });
        await sleep(100);
        await clickAt(send, pos.x, pos.y);
        await sleep(500);
      }

      // Verify this one
      r = await eval_(`
        const dd = document.querySelectorAll('.select-penta-design.table-select');
        const visible = Array.from(dd).filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0 && !el.className.includes('duration'));
        return visible[${i}]?.textContent?.trim()?.substring(0, 20) || 'unknown';
      `);
      console.log(`  Value: ${r}`);
    }
  }

  // Final save
  console.log("\n=== Saving ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
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
    console.log("URL:", result.url);

    // Check if we moved to step 3
    if (result.body.includes('Description') && result.body.includes('FAQ')) {
      console.log("Advanced to Description & FAQ step!");
    }
    console.log("Body:", result.body.substring(0, 400));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
