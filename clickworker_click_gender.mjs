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

  // Get dropdown position
  let r = await eval_(`
    const sel = document.querySelector('#user_gender');
    const rect = sel.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), h: Math.round(rect.height) });
  `);
  const pos = JSON.parse(r);
  console.log("Dropdown at:", r);

  // Click to open dropdown
  await clickAt(send, pos.x, pos.y);
  await sleep(500);

  // The native select dropdown opens with options stacked below
  // "Male" is the first option after blank, so click slightly below the dropdown
  // Each option is roughly the same height as the select (~30-40px)
  // Option positions: blank=0, Male=1, Female=2, etc.
  // Male should be about 1 option height below the dropdown
  const optionHeight = pos.h || 30;
  const maleY = pos.y + optionHeight; // One option below current position

  await clickAt(send, pos.x, maleY);
  console.log("Clicked Male option at y:", maleY);
  await sleep(500);

  // Check result
  r = await eval_(`
    const sel = document.querySelector('#user_gender');
    return 'Selected: ' + sel.options[sel.selectedIndex].text + ' (value: ' + sel.value + ')';
  `);
  console.log("Result:", r);

  // If still not Male, try different approach - use keyboard after focusing
  if (!r.includes('Male')) {
    console.log("Retrying with keyboard approach...");
    // Focus the select
    await eval_(`document.querySelector('#user_gender').focus()`);
    await sleep(200);
    // Press down arrow to move to first option (Male)
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown", windowsVirtualKeyCode: 40 });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown", windowsVirtualKeyCode: 40 });
    await sleep(200);
    // Press Enter to select
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    await sleep(300);

    r = await eval_(`
      const sel = document.querySelector('#user_gender');
      return 'Selected: ' + sel.options[sel.selectedIndex].text + ' (value: ' + sel.value + ')';
    `);
    console.log("After keyboard:", r);
  }

  // Screenshot to verify
  const screenshot = await send("Page.captureScreenshot", {
    format: "png",
    clip: { x: 540, y: 155, width: 200, height: 45, scale: 1 }
  });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_gender2.png', Buffer.from(screenshot.data, 'base64'));
  console.log("Screenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
