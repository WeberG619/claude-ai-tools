// Debug + click Upwork category
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

  // Use XPath or textContent matching to find the "Writing" item
  let r = await eval_(`
    // Find all elements containing exactly "Writing" as visible text
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const results = [];
    while (walker.nextNode()) {
      if (walker.currentNode.textContent.trim() === 'Writing') {
        const el = walker.currentNode.parentElement;
        if (el && el.getBoundingClientRect().height > 0) {
          results.push({
            text: 'Writing',
            tag: el.tagName,
            class: (el.className || '').substring(0, 60),
            parentTag: el.parentElement?.tagName || '',
            parentClass: (el.parentElement?.className || '').substring(0, 60),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
            w: Math.round(el.getBoundingClientRect().width),
            h: Math.round(el.getBoundingClientRect().height)
          });
        }
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Writing text nodes:", r);
  const writingNodes = JSON.parse(r);

  // Click the Writing element
  if (writingNodes.length > 0) {
    // Find the one that's likely a clickable category (reasonable size)
    const target = writingNodes.find(n => n.h > 20 && n.h < 100 && n.w > 50) || writingNodes[0];
    console.log(`Clicking Writing at (${target.x}, ${target.y}), parent: ${target.parentTag}.${target.parentClass}`);

    // Click the parent element for better event capture
    const parentY = target.y;
    await clickAt(send, target.x, parentY);
    await sleep(2000);

    // Check page state
    r = await eval_(`
      return JSON.stringify({
        body: document.body.innerText.substring(0, 600),
        url: location.href
      });
    `);
    console.log("After click:", JSON.parse(r).body.substring(0, 300));

    // Look for subcategories that appeared
    r = await eval_(`
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const texts = [];
      while (walker.nextNode()) {
        const t = walker.currentNode.textContent.trim();
        if (t.length > 5 && t.length < 50) {
          const el = walker.currentNode.parentElement;
          const rect = el.getBoundingClientRect();
          if (rect.y > 300 && rect.y < 800 && rect.height > 10 && rect.height < 80) {
            texts.push({
              text: t,
              tag: el.tagName,
              class: (el.className || '').substring(0, 40),
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2)
            });
          }
        }
      }
      return JSON.stringify(texts);
    `);
    console.log("\nVisible text items in middle area:", r);
    const midItems = JSON.parse(r);

    // Select subcategories
    for (const target of ['Content Writing', 'Proofreading', 'Editing', 'Resume', 'Blog']) {
      const match = midItems.find(m => m.text.includes(target));
      if (match) {
        console.log(`  Selecting: "${match.text}"`);
        await clickAt(send, match.x, match.y);
        await sleep(500);
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
      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
      r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 300) })`);
      console.log("\nNext page:", r);
    }
  } else {
    console.log("No Writing text found! Dumping page structure...");
    r = await eval_(`
      const el = document.querySelector('[class*="category"], [class*="select"]');
      return el ? el.outerHTML.substring(0, 1000) : 'no category element found';
    `);
    console.log("HTML:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
