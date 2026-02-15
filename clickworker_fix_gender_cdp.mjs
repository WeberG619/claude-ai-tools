const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No Clickworker tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Get position of the gender dropdown
  let r = await eval_(`
    const sel = document.querySelector('#user_gender');
    const rect = sel.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
  `);
  console.log("Gender dropdown position:", r);
  const selPos = JSON.parse(r);

  // Click the dropdown to open it
  await clickAt(send, selPos.x, selPos.y);
  await sleep(500);

  // Now use DOM.selectOption via CDP to properly select "Male" (value "m")
  // First try setting via select element interaction
  await send("DOM.enable");
  const doc = await send("DOM.getDocument");
  const selectNode = await send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: '#user_gender'
  });
  console.log("Select node:", selectNode.nodeId);

  // Use Runtime to properly change the select
  r = await eval_(`
    const sel = document.querySelector('#user_gender');
    // Set selectedIndex to 1 (Male)
    sel.selectedIndex = 1;
    sel.dispatchEvent(new Event('change', { bubbles: true }));
    sel.dispatchEvent(new Event('input', { bubbles: true }));
    return 'Selected: ' + sel.options[sel.selectedIndex].text + ' (value: ' + sel.value + ')';
  `);
  console.log("After selectedIndex:", r);
  await sleep(300);

  // Click away to close dropdown
  await clickAt(send, selPos.x, selPos.y + 200);
  await sleep(500);

  // Verify
  r = await eval_(`
    const sel = document.querySelector('#user_gender');
    return 'Display: ' + sel.options[sel.selectedIndex].text + ', Value: ' + sel.value;
  `);
  console.log("Verify:", r);

  // Take screenshot to confirm
  const screenshot = await send("Page.captureScreenshot", {
    format: "png",
    clip: { x: 530, y: 160, width: 250, height: 50, scale: 1 }
  });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_gender.png', Buffer.from(screenshot.data, 'base64'));
  console.log("Screenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
