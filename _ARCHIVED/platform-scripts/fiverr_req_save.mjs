// Fix Fiverr requirements page and continue
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Detailed inspection of requirements page
  let r = await eval_(`
    // Get full visible text
    const bodyText = document.body?.innerText?.substring(0, 2000);

    // Get all visible buttons
    const buttons = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 50),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2)
      }))
      .filter(b => b.text.length > 0);

    // Get all visible form elements
    const formEls = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type,
        name: el.name || '',
        value: (el.value || '').substring(0, 40),
        placeholder: (el.placeholder || '').substring(0, 40),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y)
      }));

    return JSON.stringify({ bodyText, buttons: buttons.slice(0, 20), formEls });
  `);
  console.log(r);

  const page = JSON.parse(r);

  // Find the Save & Continue button specifically
  const saveBtn = page.buttons.find(b => b.text.includes('Save & Continue'));
  console.log("\nSave button:", saveBtn);

  if (saveBtn) {
    // Scroll to it and click via CDP mouse event
    await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Save & Continue'));
      if (btn) btn.scrollIntoView({ block: 'center' });
    `);
    await sleep(300);

    // Re-get coordinates
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Save & Continue'));
      if (!btn) return JSON.stringify({ error: 'not found' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const coords = JSON.parse(r);
    console.log("Button coords:", coords);

    // Click via CDP
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: coords.x, y: coords.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: coords.x, y: coords.y, button: "left", clickCount: 1 });
    console.log("Clicked via CDP");

    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim()
      });
    `);
    console.log("After click:", r);

    const after = JSON.parse(r);
    if (after.step === 'Requirements') {
      // Try direct navigation
      console.log("Still on requirements. Navigating directly...");
      await eval_(`window.location.href = location.href.replace('wizard=3', 'wizard=4').replace('tab=requirements', 'tab=gallery')`);
      await sleep(5000);

      try {
        r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
        console.log("After navigate:", r);
      } catch(e) {
        console.log("Lost connection (page navigated)");
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
