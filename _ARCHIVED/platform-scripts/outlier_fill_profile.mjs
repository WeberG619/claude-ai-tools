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
      expression: `(async () => { ${expr} })()`,
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Click on State/Territory dropdown (the empty select button)
  let r = await eval_(`
    // Find the State dropdown - it's the select trigger after "State or Territory"
    const selects = Array.from(document.querySelectorAll('button'))
      .filter(el => el.className.includes('SelectTrigger') && el.offsetParent !== null);
    // The state one should be the last/empty one
    const stateSelect = selects.find(el => el.textContent.trim() === '' || el.textContent.trim() === 'Select State');
    if (stateSelect) {
      stateSelect.scrollIntoView({ block: 'center' });
      const rect = stateSelect.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: stateSelect.textContent.trim() });
    }
    // Return all selects for debugging
    return JSON.stringify(selects.map(s => ({
      text: s.textContent.trim().substring(0, 40),
      rect: JSON.parse(JSON.stringify(s.getBoundingClientRect()))
    })));
  `);
  console.log("State select:", r);

  // Parse and click
  let stateData;
  try {
    stateData = JSON.parse(r);
  } catch(e) {}

  if (stateData) {
    let pos;
    if (Array.isArray(stateData)) {
      // Find the empty one or the one that's not "Select" or "United States"
      const emptyOne = stateData.find(s => s.text === '' || s.text === 'State');
      pos = emptyOne || stateData[stateData.length - 1];
      console.log("Using select:", pos.text, "at", pos.rect.x, pos.rect.y);
      await clickAt(send, Math.round(pos.rect.x + pos.rect.width/2), Math.round(pos.rect.y + pos.rect.height/2));
    } else {
      await clickAt(send, stateData.x, stateData.y);
    }
    await sleep(2000);

    // Look for Idaho option
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('[role="option"], [data-radix-collection-item], option'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim(),
          rect: JSON.parse(JSON.stringify(el.getBoundingClientRect()))
        }));
      const idaho = options.find(o => o.text === 'Idaho');
      return JSON.stringify({ allCount: options.length, idaho, first5: options.slice(0, 5) }, null, 2);
    `);
    console.log("\nOptions:", r);

    const opts = JSON.parse(r);
    if (opts.idaho) {
      await clickAt(send, Math.round(opts.idaho.rect.x + opts.idaho.rect.width/2), Math.round(opts.idaho.rect.y + opts.idaho.rect.height/2));
      console.log("Selected Idaho");
      await sleep(1000);
    } else if (opts.allCount > 0) {
      // Scroll to find Idaho
      console.log("Idaho not visible, need to scroll options");
      // Try JS click
      r = await eval_(`
        const opt = Array.from(document.querySelectorAll('[role="option"], [data-radix-collection-item]'))
          .find(el => el.textContent.trim() === 'Idaho');
        if (opt) { opt.click(); return 'clicked Idaho'; }
        return 'Idaho not found in options';
      `);
      console.log(r);
      await sleep(1000);
    }
  }

  // Now click "Verify phone number"
  await sleep(1000);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.includes('Verify phone number') && el.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("\nVerify phone button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    await sleep(3000);

    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("outlier"));

    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage after verify click:");
    console.log(r);

    // Check for phone input
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({ type: el.type, placeholder: el.placeholder, id: el.id, value: el.value, name: el.name }));
      return JSON.stringify(inputs, null, 2);
    `);
    console.log("\nInputs:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
