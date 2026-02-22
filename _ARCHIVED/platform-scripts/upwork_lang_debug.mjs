// Debug Upwork languages page
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Full page dump
  let r = await eval_(`
    return document.body.innerText.substring(0, 2000);
  `);
  console.log("FULL TEXT:", r);

  // Find all interactive elements
  r = await eval_(`
    const allEls = Array.from(document.querySelectorAll('select, input, button, [role="combobox"], [role="listbox"], [contenteditable], [class*="dropdown"], [class*="select"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, type: el.type || '', id: el.id || '',
        role: el.getAttribute('role') || '',
        class: (el.className || '').substring(0, 80),
        text: el.textContent.trim().substring(0, 50),
        value: (el.value || '').substring(0, 30),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));
    return JSON.stringify(allEls);
  `);
  console.log("\nAll interactive:", r);

  // Check for any error/validation messages
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="alert"], [class*="warning"], [class*="validation"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\nErrors:", r);

  // Look at the language section HTML
  r = await eval_(`
    const langSection = document.querySelector('[class*="language"], [class*="lang"]');
    if (langSection) return langSection.outerHTML.substring(0, 2000);
    // Try broader
    const mainContent = document.querySelector('main, [class*="content"], [class*="form"]');
    if (mainContent) return mainContent.innerHTML.substring(0, 3000);
    return 'none found';
  `);
  console.log("\nLanguage HTML:", r);

  // Check if there's a proficiency dropdown visible
  r = await eval_(`
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const texts = [];
    while (walker.nextNode()) {
      const t = walker.currentNode.textContent.trim();
      if (t.length > 2 && t.length < 60) {
        const el = walker.currentNode.parentElement;
        const rect = el.getBoundingClientRect();
        if (rect.y > 200 && rect.y < 700 && rect.height > 5) {
          texts.push({ text: t, y: Math.round(rect.y), tag: el.tagName });
        }
      }
    }
    return JSON.stringify(texts);
  `);
  console.log("\nVisible text:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
