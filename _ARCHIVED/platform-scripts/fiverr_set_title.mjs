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

  // Make sure we're on the edit page
  await send("Page.navigate", { url: "https://www.fiverr.com/sellers/weberg619/edit" });
  await sleep(5000);

  // Find the "Add title" edit button/pencil icon or the title field
  let r = await eval_(`
    // Look for editable title area
    const editBtns = document.querySelectorAll('[class*="edit"], [class*="pencil"], a[href*="title"], button');
    const results = [];
    for (const el of editBtns) {
      const text = el.textContent?.trim() || '';
      const ariaLabel = el.getAttribute('aria-label') || '';
      if (text.includes('Add title') || text.includes('Edit title') || ariaLabel.includes('title') || ariaLabel.includes('Edit')) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0) {
          results.push({
            tag: el.tagName,
            text: text.substring(0, 40),
            ariaLabel,
            classes: (typeof el.className === 'string' ? el.className : '').substring(0, 60),
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2)
          });
        }
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Title edit elements:", r);

  // Also look for any inline-editable title elements
  r = await eval_(`
    const els = document.querySelectorAll('[contenteditable], input[name*="title"], textarea[name*="title"], [class*="title"] input, [class*="title"] textarea');
    return JSON.stringify(Array.from(els).map(el => ({
      tag: el.tagName,
      name: el.name || '',
      type: el.type || '',
      value: el.value?.substring(0, 50) || el.textContent?.substring(0, 50) || '',
      classes: (typeof el.className === 'string' ? el.className : '').substring(0, 60),
      rect: (() => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
    })));
  `);
  console.log("\nTitle inputs:", r);

  // Try clicking on the "Add title" text area near the profile name
  // From screenshot, "Add title" with pencil is to the right of the name, around y~145
  r = await eval_(`
    const all = document.querySelectorAll('*');
    for (const el of all) {
      if (el.children.length === 0 && el.textContent.trim() === 'Add title') {
        const rect = el.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: el.textContent.trim() });
      }
    }
    return 'not found';
  `);
  console.log("\nAdd title element:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Add title");
    await sleep(2000);

    // Check for input field that appeared
    r = await eval_(`
      const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
      return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
        tag: i.tagName,
        type: i.type || '',
        name: i.name || '',
        placeholder: i.placeholder || '',
        value: i.value?.substring(0, 50) || i.textContent?.substring(0, 50) || '',
        rect: (() => { const r = i.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
      })));
    `);
    console.log("Inputs after click:", r);

    // Also check for modals
    r = await eval_(`
      const modals = document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"], [class*="popup"], [class*="Popup"]');
      return JSON.stringify(Array.from(modals).filter(m => m.offsetParent !== null).map(m => ({
        text: m.textContent?.trim().substring(0, 200),
        classes: (typeof m.className === 'string' ? m.className : '').substring(0, 60)
      })));
    `);
    console.log("\nModals:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
