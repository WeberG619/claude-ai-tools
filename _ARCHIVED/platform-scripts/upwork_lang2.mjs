// Upwork languages - scroll to dropdown, click it, select proficiency
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

  // Scroll dropdown into view and get coordinates
  let r = await eval_(`
    const combo = document.querySelector('[role="combobox"]');
    if (combo) {
      combo.scrollIntoView({ block: 'center' });
      return 'scrolled';
    }
    return 'no combobox';
  `);
  console.log("Scroll:", r);
  await sleep(500);

  // Get combobox position after scroll
  r = await eval_(`
    const combo = document.querySelector('[role="combobox"]');
    if (combo) {
      const rect = combo.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
        visible: rect.width > 0 && rect.height > 0
      });
    }
    return JSON.stringify({ error: 'none' });
  `);
  console.log("Combobox after scroll:", r);
  const combo = JSON.parse(r);

  if (!combo.error && combo.visible) {
    // Click the dropdown
    await clickAt(send, combo.x, combo.y);
    await sleep(1000);

    // Check for dropdown items
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('[role="option"], [class*="dropdown-item"], [class*="dropdown-menu"] li, [class*="dropdown"] ul li, [class*="listbox"] li'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items);
    `);
    console.log("Options:", r);
    const opts = JSON.parse(r);

    if (opts.length > 0) {
      // Look for Native or Bilingual
      const native = opts.find(o => o.text.includes('Native') || o.text.includes('Bilingual'));
      const target = native || opts[opts.length - 1];
      await clickAt(send, target.x, target.y);
      console.log(`Selected: ${target.text}`);
      await sleep(1000);
    } else {
      // Try clicking the dropdown via JS
      console.log("No options found via selector. Trying JS click...");
      r = await eval_(`
        const combo = document.querySelector('[role="combobox"]');
        if (combo) {
          combo.click();
          return 'clicked via JS';
        }
        return 'no combo';
      `);
      console.log(r);
      await sleep(1000);

      r = await eval_(`
        // Look for any visible list items or options
        const allVisible = Array.from(document.querySelectorAll('*'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return rect.y > 300 && rect.y < 600 && rect.height > 15 && rect.height < 50
              && el.offsetParent !== null
              && el.childNodes.length <= 3
              && el.textContent.trim().length > 3
              && el.textContent.trim().length < 30;
          })
          .map(el => ({
            text: el.textContent.trim(),
            tag: el.tagName,
            class: (el.className || '').substring(0, 50),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(allVisible);
      `);
      console.log("All visible in dropdown area:", r);
      const items = JSON.parse(r);

      const native2 = items.find(i => i.text.includes('Native') || i.text.includes('Bilingual') || i.text.includes('Fluent'));
      if (native2) {
        await clickAt(send, native2.x, native2.y);
        console.log(`Selected: ${native2.text}`);
        await sleep(1000);
      }
    }
  } else {
    // Try with JS approach directly
    console.log("Combobox not visible, trying direct JS interaction...");
    r = await eval_(`
      // Find the dropdown container and try to interact with it
      const dropdown = document.querySelector('.languages-dropdown') || document.querySelector('.air3-dropdown');
      if (dropdown) {
        dropdown.scrollIntoView({ block: 'center' });
        const toggle = dropdown.querySelector('.air3-dropdown-toggle');
        if (toggle) {
          toggle.click();
          return 'toggle clicked';
        }
      }
      return 'no dropdown found';
    `);
    console.log(r);
    await sleep(1000);

    // Get updated positions
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('[role="option"], li'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0 && el.getBoundingClientRect().y > 200)
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items);
    `);
    console.log("Options after JS click:", r);
    const opts2 = JSON.parse(r);
    if (opts2.length > 0) {
      const native = opts2.find(o => o.text.includes('Native') || o.text.includes('Bilingual'));
      const target = native || opts2[opts2.length - 1];
      await clickAt(send, target.x, target.y);
      console.log(`Selected: ${target.text}`);
    }
  }

  await sleep(1000);

  // Verify error cleared
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('proficiency'))
      .map(el => el.textContent.trim().substring(0, 80));
    const combo = document.querySelector('[role="combobox"]');
    const val = combo ? combo.textContent.trim() : 'no combo';
    return JSON.stringify({ errors, comboText: val });
  `);
  console.log("After selection:", r);

  // Click Next
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next' });
  `);
  await sleep(300);
  const next = JSON.parse(r);
  if (!next.error) {
    await clickAt(send, next.x, next.y);
    console.log("Clicked Next");
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 300) })`);
    console.log("\nNext page:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
