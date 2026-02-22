const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("fiverr");

  // Click on the title input to focus it
  await clickAt(send, 702, 179);
  await sleep(500);

  // Set the title value
  const title = "Python Automation & Web Scraping Specialist";
  let r = await eval_(`
    const input = document.querySelector('input[placeholder="Add title"]');
    if (input) {
      input.focus();
      const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSet.call(input, '${title}');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set: ' + input.value;
    }
    return 'no input';
  `);
  console.log("Title set:", r);
  await sleep(500);

  // Press Enter or click away to save
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await sleep(2000);

  // Click somewhere else to deselect
  await clickAt(send, 700, 400);
  await sleep(2000);

  // Verify the title
  r = await eval_(`
    // Look for the title text on page
    const all = document.querySelectorAll('*');
    for (const el of all) {
      if (el.children.length === 0 && el.textContent.includes('Python Automation')) {
        return el.textContent.trim();
      }
    }
    // Check input value
    const input = document.querySelector('input[placeholder="Add title"]');
    if (input) return 'input value: ' + input.value;
    return 'title not found';
  `);
  console.log("\nTitle verification:", r);

  // Check page header area
  r = await eval_(`
    const header = document.querySelector('.seller-profile-header, .user-profile-info, [class*="header"]');
    if (header) return header.textContent.trim().substring(0, 300);
    return document.body.innerText.substring(0, 500);
  `);
  console.log("\nHeader area:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
