// Find block option in Fiverr chat - look in conversation header area
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Look for ALL buttons in the conversation header area (between y=60 and y=200)
  console.log("=== Conversation header buttons ===");
  let r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, [role="button"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y > 60 && rect.y < 200 && rect.x > 350;
      })
      .map(el => ({
        text: el.textContent?.trim()?.substring(0, 30) || '',
        ariaLabel: el.getAttribute('aria-label') || '',
        title: el.title || '',
        class: (el.className?.toString() || '').substring(0, 80),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));
    return JSON.stringify(btns);
  `);
  console.log("Header buttons:", r);
  const headerBtns = JSON.parse(r);

  // Click each one looking for a menu with block/report
  for (const btn of headerBtns) {
    console.log(`\nClicking header btn at (${btn.x}, ${btn.y}) - "${btn.text}" aria="${btn.ariaLabel}" ${btn.w}x${btn.h}`);
    await clickAt(send, btn.x, btn.y);
    await sleep(1500);

    r = await eval_(`
      // Look for popover/dropdown that appeared
      const items = Array.from(document.querySelectorAll('[class*="popover"] *, [class*="dropdown"] *, [class*="menu"] *, [role="menu"] *, [role="menuitem"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 100 && rect.y < 500 && rect.width > 50 && rect.height > 15 && rect.height < 60;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          tag: el.tagName,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }))
        .filter(l => l.text.length > 0 && l.text.length < 40);

      // Deduplicate
      const seen = new Set();
      const unique = items.filter(i => {
        if (seen.has(i.text)) return false;
        seen.add(i.text);
        return true;
      });
      return JSON.stringify(unique);
    `);
    console.log("Popup items:", r);
    const items = JSON.parse(r);

    const blockItem = items.find(i => i.text.toLowerCase().includes('block'));
    const reportItem = items.find(i => i.text.toLowerCase().includes('report'));
    const spamItem = items.find(i => i.text.toLowerCase().includes('spam'));

    if (blockItem) {
      console.log(`\n*** FOUND BLOCK: "${blockItem.text}" at (${blockItem.x}, ${blockItem.y}) ***`);
      await clickAt(send, blockItem.x, blockItem.y);
      await sleep(2000);

      // Confirm
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({ text: el.textContent.trim().substring(0, 30), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }))
          .filter(b => b.text.toLowerCase().includes('block') || b.text.toLowerCase().includes('confirm') || b.text.toLowerCase().includes('yes'));
        return JSON.stringify(btns);
      `);
      console.log("Confirm buttons:", r);
      const confirms = JSON.parse(r);
      if (confirms.length > 0) {
        await clickAt(send, confirms[0].x, confirms[0].y);
        await sleep(2000);
        console.log("BLOCKED!");
      }
      break;
    }

    if (reportItem) {
      console.log(`\n*** FOUND REPORT: "${reportItem.text}" at (${reportItem.x}, ${reportItem.y}) ***`);
      await clickAt(send, reportItem.x, reportItem.y);
      await sleep(2000);
      // Continue looking for block too
    }

    if (spamItem) {
      console.log(`\n*** FOUND SPAM: "${spamItem.text}" at (${spamItem.x}, ${spamItem.y}) ***`);
      await clickAt(send, spamItem.x, spamItem.y);
      await sleep(2000);
    }

    // Close any popup by clicking elsewhere
    await clickAt(send, 600, 500);
    await sleep(500);
  }

  // Also try right-clicking on the conversation in the sidebar for context menu
  console.log("\n=== Trying context menu on conversation ===");
  r = await eval_(`
    const conv = Array.from(document.querySelectorAll('[class*="contact"]'))
      .find(el => el.textContent?.includes('Jamie') && el.offsetParent !== null);
    if (conv) {
      const rect = conv.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  const convPos = JSON.parse(r);
  if (!convPos.error) {
    // Right-click (context menu)
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: convPos.x, y: convPos.y, button: "right", clickCount: 1 });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: convPos.x, y: convPos.y, button: "right", clickCount: 1 });
    await sleep(1500);

    r = await eval_(`
      const items = Array.from(document.querySelectorAll('[class*="context"] *, [class*="popover"] *, [class*="menu"] *'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.width > 50 && rect.height > 15 && rect.height < 60;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }))
        .filter(l => l.text.length > 0 && l.text.length < 40);
      const seen = new Set();
      return JSON.stringify(items.filter(i => { if (seen.has(i.text)) return false; seen.add(i.text); return true; }));
    `);
    console.log("Context menu:", r);

    const ctxItems = JSON.parse(r);
    const blockCtx = ctxItems.find(i => i.text.toLowerCase().includes('block') || i.text.toLowerCase().includes('report') || i.text.toLowerCase().includes('spam') || i.text.toLowerCase().includes('mark'));
    if (blockCtx) {
      console.log(`Found "${blockCtx.text}" - clicking!`);
      await clickAt(send, blockCtx.x, blockCtx.y);
      await sleep(2000);
    }
  }

  // Check final state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: (document.body?.innerText || '').substring(0, 300)
    });
  `);
  console.log("\nFinal:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
