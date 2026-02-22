// Find and click Upwork category items
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

  // Find ALL clickable elements that match category names
  let r = await eval_(`
    const allElements = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent.trim();
        const ownText = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 ? text : '';
        return el.offsetParent !== null
          && (ownText === 'Writing' || ownText === 'Admin Support' || ownText === 'Engineering & Architecture')
          && el.getBoundingClientRect().height > 10
          && el.getBoundingClientRect().height < 100;
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        class: (el.className || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height),
        clickable: el.style.cursor === 'pointer' || el.onclick !== null || el.tagName === 'A' || el.tagName === 'BUTTON'
      }));
    return JSON.stringify(allElements);
  `);
  console.log("Writing elements:", r);

  // Try to click "Writing"
  const elems = JSON.parse(r);
  const writingEl = elems.find(e => e.text === 'Writing');
  if (writingEl) {
    console.log(`Clicking Writing at (${writingEl.x}, ${writingEl.y})`);
    await clickAt(send, writingEl.x, writingEl.y);
    await sleep(2000);

    // Check what changed
    r = await eval_(`
      return JSON.stringify({
        body: document.body.innerText.substring(0, 600),
        selected: Array.from(document.querySelectorAll('[class*="selected"], [aria-selected="true"], [class*="active"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 30))
      });
    `);
    console.log("After Writing click:", r);

    // Now look for subcategories
    r = await eval_(`
      const subText = document.body.innerText;
      const subStart = subText.indexOf('select 1 to 3') || subText.indexOf('Select up to');
      if (subStart > 0) {
        return subText.substring(subStart, subStart + 300);
      }
      return subText.substring(200, 600);
    `);
    console.log("Subcategories area:", r);

    // Find subcategory clickable items
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const text = el.textContent.trim();
          const ownText = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 ? text : '';
          return el.offsetParent !== null
            && ownText.length > 5 && ownText.length < 40
            && el.getBoundingClientRect().y > 400
            && el.getBoundingClientRect().height > 10
            && el.getBoundingClientRect().height < 80
            && !ownText.includes('Skip') && !ownText.includes('Back') && !ownText.includes('Next');
        })
        .map(el => ({
          text: el.textContent.trim(),
          tag: el.tagName,
          class: (el.className || '').substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items);
    `);
    console.log("Subcategory items:", r);
    const subItems = JSON.parse(r);

    // Click relevant subcategories (up to 3)
    const targets = ['Content Writing', 'Resume', 'Proofreading', 'Editing', 'Technical', 'Blog', 'Article'];
    let clicked = 0;
    for (const target of targets) {
      if (clicked >= 3) break;
      const match = subItems.find(s => s.text.includes(target));
      if (match) {
        console.log(`  Selecting: "${match.text}"`);
        await clickAt(send, match.x, match.y);
        await sleep(500);
        clicked++;
      }
    }
    if (clicked === 0 && subItems.length > 0) {
      // Just click first 3
      for (let i = 0; i < Math.min(3, subItems.length); i++) {
        console.log(`  Selecting: "${subItems[i].text}"`);
        await clickAt(send, subItems[i].x, subItems[i].y);
        await sleep(500);
      }
    }
  }

  // Click Next
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next' });
  `);
  const next = JSON.parse(r);
  if (!next.error) {
    await clickAt(send, next.x, next.y);
    await sleep(5000);
  }

  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 400) })`);
  console.log("\nNext page:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
