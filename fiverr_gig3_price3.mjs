// Fix delivery times, premium revision, then save
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function selectPenta(send, eval_, dropdownX, dropdownY, optionText) {
  await clickAt(send, dropdownX, dropdownY);
  await sleep(600);
  const r = await eval_(`
    const opts = Array.from(document.querySelectorAll('.table-select-option'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(opts);
  `);
  const opts = JSON.parse(r);
  const target = opts.find(o => o.text.toLowerCase().includes(optionText.toLowerCase()));
  if (target) {
    await clickAt(send, target.x, target.y);
    await sleep(400);
    return target.text;
  }
  // Close dropdown by pressing Escape
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  return `NOT FOUND: "${optionText}" in [${opts.map(o => o.text).join(', ')}]`;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // SCROLL TO TOP
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // === DELIVERY TIMES ===
  console.log("=== Delivery Times ===");

  // Get fresh positions after scrolling to top
  let r = await eval_(`
    const pentaSelects = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => {
        const text = el.textContent.trim();
        return el.offsetParent !== null
          && !el.querySelector('.select-penta-design')
          && (text.includes('Delivery') || text === 'Delivery Time')
          && el.getBoundingClientRect().y > 0
          && el.getBoundingClientRect().y < 1200;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(pentaSelects);
  `);
  console.log("Delivery dropdowns:", r);
  const delivDropdowns = JSON.parse(r);

  if (delivDropdowns.length >= 3) {
    for (let i = 0; i < 3; i++) {
      const texts = ["3 days", "2 days", "1 day"];
      const result = await selectPenta(send, eval_, delivDropdowns[i].x, delivDropdowns[i].y, texts[i]);
      console.log(`  Delivery ${i+1}: ${result}`);
    }
  } else {
    console.log("Need to scroll to find delivery dropdowns");
    // Scroll to the first delivery area
    await eval_(`
      const el = document.querySelector('.select-penta-design');
      if (el) el.scrollIntoView({ block: 'center' });
    `);
    await sleep(500);

    r = await eval_(`
      const pentaSelects = Array.from(document.querySelectorAll('.select-penta-design'))
        .filter(el => {
          const text = el.textContent.trim();
          return el.offsetParent !== null
            && !el.querySelector('.select-penta-design')
            && (text.includes('Delivery') || text === 'Delivery Time')
            && el.getBoundingClientRect().y > 0;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 20),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(pentaSelects);
    `);
    console.log("After scroll:", r);
    const dd2 = JSON.parse(r);
    for (let i = 0; i < Math.min(dd2.length, 3); i++) {
      const texts = ["3 days", "2 days", "1 day"];
      const result = await selectPenta(send, eval_, dd2[i].x, dd2[i].y, texts[i]);
      console.log(`  Delivery ${i+1}: ${result}`);
    }
  }

  // === PREMIUM REVISION ===
  console.log("\n=== Premium Revision ===");
  r = await eval_(`
    // Find the 3rd revision-like dropdown that shows "Select" in the package area
    const revDropdowns = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => {
        const text = el.textContent.trim();
        return el.offsetParent !== null
          && !el.querySelector('.select-penta-design')
          && (text === 'Select' || /^\\d+$/.test(text) || text === 'UNLIMITED')
          && el.getBoundingClientRect().y > 0
          && el.getBoundingClientRect().y < 1200
          && el.getBoundingClientRect().x > 700;  // Premium column is rightmost
      })
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(revDropdowns);
  `);
  console.log("Premium revision dropdowns:", r);
  const premRevs = JSON.parse(r);

  // Find the one that's "Select" (not yet set) - it's the revision dropdown
  const premRev = premRevs.find(d => d.text === 'Select');
  if (premRev) {
    const result = await selectPenta(send, eval_, premRev.x, premRev.y, "unlimited");
    console.log(`  Premium revision: ${result}`);
  } else {
    console.log("  Premium revision already set or not found");
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(1000);

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
    await sleep(8000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors,
        body: document.body?.innerText?.substring(0, 200)
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
