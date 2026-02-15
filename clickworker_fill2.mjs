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

  // Fill all fields at once
  let r = await eval_(`
    const setVal = (selector, value) => {
      const el = document.querySelector(selector);
      if (!el) return false;
      const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSet.call(el, value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new Event('blur', { bubbles: true }));
      return true;
    };

    // Gender - already set to Male via selectedIndex
    const sel = document.querySelector('#user_gender');
    sel.selectedIndex = 1;
    sel.dispatchEvent(new Event('change', { bubbles: true }));

    setVal('#user_first_name', 'Weber');
    setVal('#user_last_name', 'Gouin');
    setVal('#user_username', 'weberg619');
    setVal('#user_email', 'weberg619@gmail.com');

    return JSON.stringify({
      gender: sel.options[sel.selectedIndex].text,
      firstName: document.querySelector('#user_first_name').value,
      lastName: document.querySelector('#user_last_name').value,
      username: document.querySelector('#user_username').value,
      email: document.querySelector('#user_email').value
    });
  `);
  console.log("Filled:", r);

  // Take screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_filled.png', Buffer.from(screenshot.data, 'base64'));
  console.log("Screenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
